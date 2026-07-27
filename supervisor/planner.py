"""
Supervisor Planner

Responsible for decomposing a high-level Goal into a structured ExecutionPlan.
Uses rule-based capability inference to generate tasks for the router.

Architecture Layer: Supervisor / Planner
"""

import re
from typing import List, Tuple

from core.exceptions.base import PlanningError
from core.logging.logger import logger
from core.models.domain import ExecutionPlan, Goal, Task
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

    async def create_plan(self, goal: Goal) -> ExecutionPlan:
        """
        Decomposes a Goal into an ordered ExecutionPlan containing Task items.

        Args:
            goal: Target user goal.

        Returns:
            ExecutionPlan: Sequenced plan of tasks.

        Raises:
            PlanningError: If the goal description is empty.
        """
        logger.info(
            "SupervisorPlanner: creating plan",
            goal_id=goal.id,
            description=goal.description,
        )

        if not goal.description.strip():
            raise PlanningError(
                "Cannot create plan: goal description is empty.",
                details=f"goal_id={goal.id}",
            )

        capabilities = _infer_capabilities(goal.description)
        tasks = []
        previous_task_id = None

        for cap in capabilities:
            task = Task(
                id=generate_uuid(),
                goal_id=goal.id,
                name=f"{cap} task",
                description=f"Perform {cap} to help achieve: {goal.description}",
                required_capability=cap,
                priority="high",
                dependencies=[previous_task_id] if previous_task_id else [],
            )
            tasks.append(task)
            previous_task_id = task.id

        plan = ExecutionPlan(
            id=generate_uuid(),
            goal_id=goal.id,
            tasks=tasks,
        )

        logger.info(
            "SupervisorPlanner: plan created",
            plan_id=plan.id,
            task_count=len(plan.tasks),
            capabilities=capabilities,
        )
        return plan
