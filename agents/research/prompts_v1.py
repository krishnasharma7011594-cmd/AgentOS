"""
Research Agent Prompt Library — Version 1

Centralises all prompts used by the Research Agent so they can be:
  - Versioned (v1, v2, ...) without touching agent logic
  - Reviewed and improved independently from the agent lifecycle
  - Tested in isolation to verify expected LLM behaviour

To use a different prompt version, update the import in agent.py:
    from agents.research.prompts_v1 import SYSTEM_CONTEXT
↓
    from agents.research.prompts_v2 import SYSTEM_CONTEXT

Architecture Layer: Agents / Research
"""

# ---------------------------------------------------------------------------
# System Context
# ---------------------------------------------------------------------------
# Injected by AgentLifecycle._extra_context() into the first user turn.
# Keeps the ReAct system prompt generic while this gives research-specific
# guidance — separation of concerns between lifecycle and domain expertise.

SYSTEM_CONTEXT = """\
You are an expert Research Agent specializing in accurate, well-structured \
information synthesis.

Guidelines:
- Prioritize current information — use the web_search tool when you need \
up-to-date facts.
- Structure your final answer clearly with headings, bullet points, or \
numbered lists where appropriate.
- If search results are insufficient, acknowledge what you know and what \
remains uncertain.
- Cite tool observations in your reasoning to show your work.
- Keep the final answer concise but comprehensive.
"""

# ---------------------------------------------------------------------------
# Task Prompt Templates
# ---------------------------------------------------------------------------
# These are optional templates for pre-processing task descriptions before
# they are sent to the ReAct loop. Phase 3 uses them for display only;
# Phase 4+ may use them to inject structured context.

RESEARCH_TASK_TEMPLATE = """\
Research Request: {description}

Please research this topic thoroughly and provide a comprehensive answer.
"""

SUMMARIZATION_TASK_TEMPLATE = """\
Summarization Request: {description}

Please provide a concise, structured summary of the provided information.
"""

DOCUMENTATION_TASK_TEMPLATE = """\
Documentation Lookup: {description}

Please look up and explain the requested documentation or technical concept.
"""

# ---------------------------------------------------------------------------
# Capability → Template Mapping
# ---------------------------------------------------------------------------
# Maps AgentCapability names to the prompt template to use.
# Looked up by ResearchAgent when building the task user message.

CAPABILITY_TEMPLATES = {
    "web_research": RESEARCH_TASK_TEMPLATE,
    "summarization": SUMMARIZATION_TASK_TEMPLATE,
    "documentation_lookup": DOCUMENTATION_TASK_TEMPLATE,
}
