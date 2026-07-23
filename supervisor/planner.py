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
    (r"\b(summarize|summary|summarization)\b", "summarization"),
    (r"\b(document|docs|documentation|readme|manual|api ref)\b", "documentation_lookup"),
    (
        r"\b(research|investigate|explain|what is|what are|how does|tell me about|describe)\b",
        "web_research",
    ),
]

_DEFAULT_CAPABILITY = "web_research"


def _infer_capability(description: str) -> str:
    """Infers the required capability key from goal text using pattern matching."""
    lower = description.lower()
    for pattern, capability in _CAPABILITY_KEYWORD_MAP:
        if re.search(pattern, lower):
            return str(capability)
    return _DEFAULT_CAPABILITY


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

        capability = _infer_capability(goal.description)

        task = Task(
            id=generate_uuid(),
            goal_id=goal.id,
            name=goal.description,
            description=f"Research and provide a comprehensive answer to: {goal.description}",
            required_capability=capability,
            priority="high",
        )

        plan = ExecutionPlan(
            id=generate_uuid(),
            goal_id=goal.id,
            tasks=[task],
        )

        logger.info(
            "SupervisorPlanner: plan created",
            plan_id=plan.id,
            task_count=len(plan.tasks),
            capability=capability,
        )
        return plan
