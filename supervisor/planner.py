"""
Supervisor Planner

Responsible for decomposing a high-level Goal into a structured ExecutionPlan.
Uses rule-based capability inference to generate tasks for the router.

Phase 5 adds:
  - create_recovery_tasks(ReplanRequest): generates targeted recovery tasks
    when the DecisionEngine issues a REPLAN decision.

Architecture Layer: Supervisor / Planner
"""

import re
from typing import List, Tuple

from core.exceptions.base import PlanningError
from core.logging.logger import logger
from core.models.context import PlannerInput
from core.models.domain import ExecutionPlan, Goal, ReplanRequest, Task
from core.utils.helpers import generate_uuid

# Deterministic keyword patterns mapped to capability keys
_CAPABILITY_KEYWORD_MAP: List[Tuple[str, str]] = [
    (
        r"\b(research|investigate|explain|what is|what are|how does|tell me about|describe)\b",
        "web_research",
    ),
    (r"\b(code|generate|python|script|program)\b", "code_generation"),
    (r"\b(review|pr|pull request)\b", "pr_review"),
    (r"\b(summarize|summary|summarization)\b", "summarization"),
    (r"\b(document|docs|documentation|readme|manual|api ref)\b", "documentation_lookup"),
]

_DEFAULT_CAPABILITY = "web_research"


def _infer_capabilities(description: str) -> List[str]:
    """Infers the required capabilities from goal text using pattern matching."""
    lower = description.lower()
    capabilities = []
    for pattern, capability in _CAPABILITY_KEYWORD_MAP:
        if re.search(pattern, lower) and capability not in capabilities:
            capabilities.append(str(capability))
    if not capabilities:
        capabilities.append(_DEFAULT_CAPABILITY)
    return capabilities


class SupervisorPlanner:
    """
    Supervisor subcomponent responsible for goal decomposition.

    Owns the transformation of Goal -> ExecutionPlan.
    Does NOT assign tasks to specific agent instances — task routing belongs to SupervisorRouter.

    Currently uses rule-based capability inference.
    TODO: Replace deterministic keyword planner with LLM-driven planning in Phase 3.
    """

    async def create_plan(self, input_data: PlannerInput) -> ExecutionPlan:
        """
        Decomposes a Goal into an ordered ExecutionPlan containing Task items.

        Args:
            input_data: PlannerInput containing the goal description and context.

        Returns:
            ExecutionPlan: Sequenced plan of tasks.

        Raises:
            PlanningError: If the goal description is empty.
        """
        logger.info(
            "SupervisorPlanner: creating plan",
            goal_id=input_data.goal_id,
            description=input_data.goal_description,
            has_context=input_data.context is not None and not input_data.context.is_empty,
        )

        if not input_data.goal_description.strip():
            raise PlanningError(
                "Cannot create plan: goal description is empty.",
                details=f"goal_id={input_data.goal_id}",
            )

        # In LLM-driven planning (Phase 3+), we would serialize the ContextBundle here
        # into a prompt string and pass it to the LLM layer.
        
        capabilities = _infer_capabilities(input_data.goal_description)
        tasks = []
        previous_task_id = None

        for cap in capabilities:
            task = Task(
                id=generate_uuid(),
                goal_id=input_data.goal_id,
                name=f"{cap} task",
                description=f"Perform {cap} to help achieve: {input_data.goal_description}",
                required_capability=cap,
                priority="high",
                dependencies=[previous_task_id] if previous_task_id else [],
            )
            tasks.append(task)
            previous_task_id = task.id

        plan = ExecutionPlan(
            id=generate_uuid(),
            goal_id=input_data.goal_id,
            tasks=tasks,
        )

        logger.info(
            "SupervisorPlanner: plan created",
            plan_id=plan.id,
            task_count=len(plan.tasks),
            capabilities=capabilities,
        )
        return plan

    async def create_recovery_tasks(self, request: ReplanRequest) -> List[Task]:
        """
        Generate recovery tasks in response to a REPLAN decision.

        Creates one follow-up task that retries the failing capability
        using a slightly different, diagnostics-oriented description.
        This provides a minimal but structured recovery path.

        Args:
            request: ReplanRequest with context from the failed task.

        Returns:
            List of new Task objects to insert into the ExecutionGraph.
        """
        logger.info(
            "SupervisorPlanner: generating recovery tasks",
            goal_id=request.goal_id,
            failed_task_id=request.failed_task_id,
            failure_category=(
                request.evaluation.failure_category.value
                if request.evaluation.failure_category
                else "unknown"
            ),
        )

        recovery_description = (
            f"Recovery task for failed task '{request.failed_task_id}'. "
            f"Previous failure: {request.evaluation.notes}. "
            f"Context: {request.context_summary[:300]}"
        )

        recovery_task = Task(
            id=generate_uuid(),
            goal_id=request.goal_id,
            name="Recovery: web_research",
            description=recovery_description,
            required_capability="web_research",
            priority="high",
            dependencies=[],
        )

        logger.info(
            "SupervisorPlanner: recovery task created",
            recovery_task_id=recovery_task.id,
        )
        return [recovery_task]
