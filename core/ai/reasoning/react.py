"""
ReAct Reasoning Engine

Implements the ReAct (Reasoning + Acting) pattern for AgentOS agents.

ReAct drives an iterative loop:
  1. Think   — LLM receives task + tool menu + history, produces a Thought.
  2. Act     — LLM selects a tool and provides Action Input parameters.
  3. Observe — ToolRegistry executes the tool; result is appended to history.
  4. Repeat  until the LLM emits a "Final Answer:" line or max_steps is reached.

The reasoner is stateless across calls: all context is carried in the
reasoning_steps list so the same instance can serve concurrent requests.

This module replaces the trivial BaseReasoningEngine stub with a concrete
implementation that all agents (Research, Coding, GitHub, Finance) can share.

Architecture Layer: Core / AI / Reasoning
"""

import json
import re
from typing import Any, Dict, List, Optional, Tuple

from core.ai.providers.base import BaseLLMProvider
from core.logging.logger import logger
from core.models.domain import (
    Message,
    Observation,
    ReasoningStep,
    RoleEnum,
    Task,
    ToolCall,
    ToolResult,
)
from core.tools.registry import ToolRegistry

# ---------------------------------------------------------------------------
# Prompt Templates
# ---------------------------------------------------------------------------

# System prompt injected at position 0 of every ReAct conversation.
# {tool_descriptions} is filled in by _build_messages() at call time.
REACT_SYSTEM_TEMPLATE = """\
You are a capable AI agent with access to the following tools:

{tool_descriptions}

Use this EXACT format for every response until you have a final answer:

Thought: [Your internal reasoning about what to do next]
Action: [tool_name]
Action Input: {{"key": "value"}}

When you have enough information to fully answer the user's request, use:

Thought: [Your reasoning about why you have enough information]
Final Answer: [Your complete, well-structured answer]

Rules:
- Always start with "Thought:".
- "Action:" must exactly match a tool name from the list above.
- "Action Input:" must be valid JSON.
- Never fabricate tool results — always execute a tool if you need external data.
- If a tool fails, acknowledge it in your next Thought and try another approach.
"""


class ReactReasoner:
    """
    Stateless ReAct loop executor shared across all AgentOS agents.

    Args:
        llm_provider:  Injected LLM backend (Gemini, Groq, etc.).
        tool_registry: Injected ToolRegistry with all registered tools.
        max_steps:     Maximum Think→Act→Observe iterations before forcing a
                       final answer from the accumulated context.
    """

    def __init__(
        self,
        llm_provider: BaseLLMProvider,
        tool_registry: ToolRegistry,
        max_steps: int = 3,
    ) -> None:
        self._llm = llm_provider
        self._registry = tool_registry
        self._max_steps = max_steps

    # ------------------------------------------------------------------
    # Public Interface
    # ------------------------------------------------------------------

    async def run(
        self,
        task: Task,
        extra_context: Optional[str] = None,
    ) -> Tuple[List[ReasoningStep], str]:
        """
        Execute the full ReAct loop for the given task.

        Args:
            task:          The Task domain model containing the user objective.
            extra_context: Optional additional instructions prepended to the
                           user message (e.g. agent-specific guidelines).

        Returns:
            A tuple of (reasoning_steps, final_answer).
            reasoning_steps is the full trace for observability/logging.
            final_answer is the text returned to the Supervisor.
        """
        logger.info("react_loop_start", task_id=task.id, max_steps=self._max_steps)

        tool_descriptions = self._registry.get_tool_descriptions()
        system_prompt = REACT_SYSTEM_TEMPLATE.format(tool_descriptions=tool_descriptions)

        # Conversation history — grows with each iteration
        messages: List[Message] = [
            Message(role=RoleEnum.SYSTEM, content=system_prompt),
        ]

        # Build the initial user message
        user_content = task.description
        if extra_context:
            user_content = f"{extra_context}\n\n{user_content}"
        messages.append(Message(role=RoleEnum.USER, content=user_content))

        reasoning_steps: List[ReasoningStep] = []

        for step_index in range(1, self._max_steps + 1):
            logger.info("react_step_start", task_id=task.id, step=step_index)

            # ---- Think -------------------------------------------------------
            llm_output = await self._llm.complete(messages)
            logger.debug("react_llm_output", step=step_index, output=llm_output[:300])

            # Append assistant turn so the next step sees full conversation
            messages.append(Message(role=RoleEnum.ASSISTANT, content=llm_output))

            # ---- Parse -------------------------------------------------------
            step = _parse_llm_output(llm_output, step_index)
            reasoning_steps.append(step)

            logger.info(
                "react_step_parsed",
                task_id=task.id,
                step=step_index,
                is_final=step.is_final,
                action=step.action,
            )

            # ---- Final Answer? -----------------------------------------------
            if step.is_final:
                final_answer = step.final_answer or step.thought
                logger.info(
                    "react_loop_complete",
                    task_id=task.id,
                    steps_taken=step_index,
                    answer_length=len(final_answer),
                )
                return reasoning_steps, final_answer

            # ---- Act ---------------------------------------------------------
            if step.action is None:
                # LLM produced a Thought without an Action — treat as answer
                logger.warning("react_no_action", task_id=task.id, step=step_index)
                return reasoning_steps, step.thought

            tool_call = ToolCall(
                tool_name=step.action,
                parameters=step.action_input or {},
            )
            tool_result: ToolResult = await self._registry.execute(tool_call)

            # ---- Observe -----------------------------------------------------
            observation_content = _build_observation_text(tool_result, step_index)
            observation = Observation(
                step=step_index,
                tool_result=tool_result,
                content=observation_content,
            )

            # Update the last reasoning step with the observation text
            reasoning_steps[-1] = reasoning_steps[-1].model_copy(
                update={"observation": observation_content}
            )

            # Append the observation as a tool-role message for the next LLM turn
            messages.append(
                Message(role=RoleEnum.TOOL, content=f"Observation: {observation.content}")
            )

            logger.info(
                "react_observation",
                task_id=task.id,
                step=step_index,
                tool=tool_result.tool_name,
                success=tool_result.success,
            )

        # ---- Max steps reached — synthesise answer from gathered context -----
        logger.warning(
            "react_max_steps_reached",
            task_id=task.id,
            steps=self._max_steps,
        )
        fallback = await self._synthesise_fallback(task, messages)
        return reasoning_steps, fallback

    # ------------------------------------------------------------------
    # Private Helpers
    # ------------------------------------------------------------------

    async def _synthesise_fallback(self, task: Task, messages: List[Message]) -> str:
        """
        When max_steps is exhausted without a Final Answer, ask the LLM to
        summarise what it has gathered so far into a coherent response.
        """
        messages.append(
            Message(
                role=RoleEnum.USER,
                content=(
                    "You have reached the maximum number of reasoning steps. "
                    "Based on all observations so far, provide your best Final Answer now."
                ),
            )
        )
        return await self._llm.complete(messages)


# ---------------------------------------------------------------------------
# Parsing Utilities
# ---------------------------------------------------------------------------

# These are module-level functions (not methods) so they can be unit-tested
# in isolation without constructing a full ReactReasoner instance.


def _parse_llm_output(raw_output: str, step: int) -> ReasoningStep:
    """
    Parse raw LLM text into a structured ReasoningStep.

    Expected formats:
      Thought: ...
      Action: tool_name
      Action Input: {...}

    OR:
      Thought: ...
      Final Answer: ...

    Falls back gracefully if the LLM deviates from the expected format.
    """
    thought = _extract_field(raw_output, "Thought") or raw_output.strip()
    final_answer = _extract_field(raw_output, "Final Answer")

    if final_answer:
        return ReasoningStep(
            step=step,
            thought=thought,
            is_final=True,
            final_answer=final_answer,
        )

    action = _extract_field(raw_output, "Action")
    action_input_raw = _extract_field(raw_output, "Action Input")
    action_input: Optional[Dict[str, Any]] = None

    if action_input_raw:
        action_input = _safe_json_parse(action_input_raw)

    return ReasoningStep(
        step=step,
        thought=thought,
        action=action,
        action_input=action_input,
        is_final=False,
    )


def _extract_field(text: str, field: str) -> Optional[str]:
    """
    Extract the value of a labelled field from ReAct-formatted text.

    Example:
        _extract_field("Thought: I need to search\nAction: web_search", "Thought")
        → "I need to search"
    """
    # Match "Field: <value up to next labelled field or end of string>"
    pattern = rf"^{re.escape(field)}:\s*(.+?)(?=\n[A-Za-z ]+:|\Z)"
    match = re.search(pattern, text, re.DOTALL | re.MULTILINE)
    if match:
        return match.group(1).strip()
    return None


def _safe_json_parse(raw: str) -> Optional[Dict[str, Any]]:
    """
    Attempt to parse a JSON string, returning None rather than raising on failure.

    The LLM sometimes wraps JSON in backticks or adds trailing text — we strip
    those defensively before parsing.
    """
    # Strip markdown code fences if present
    cleaned = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`").strip()
    try:
        result = json.loads(cleaned)
        if isinstance(result, dict):
            return result
        return {"value": result}
    except (json.JSONDecodeError, ValueError):
        # If the LLM gave us plain text instead of JSON, wrap it
        return {"query": cleaned}


def _build_observation_text(result: ToolResult, step: int) -> str:
    """
    Format a ToolResult into the text injected into the next LLM prompt.

    Keeps it concise — the full output is available in the ToolResult for
    tracing but we only surface what helps the LLM reason next.
    """
    if not result.success:
        return (
            f"Step {step} — Tool '{result.tool_name}' failed: {result.error}. "
            "Consider a different approach."
        )
    # Truncate very long outputs to avoid blowing the context window
    output = result.output
    if len(output) > 2000:
        output = output[:2000] + "\n... [output truncated]"
    return f"Step {step} — Tool '{result.tool_name}' returned:\n{output}"
