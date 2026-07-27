"""
DecisionEngine

Pure decision-making component for the AgentOS Adaptive Supervisor.

Receives a DecisionContext and produces a structured Decision object.
The engine never mutates the ExecutionGraph, invokes the Planner, or
emits events. All side effects are the Orchestrator's responsibility.

Architecture Layer: Supervisor / Decision (Phase 5)
"""

from core.models.domain import (
    Decision,
    DecisionContext,
    DecisionType,
    FailureCategory,
)
from supervisor.policies import RetryPolicy


class DecisionEngine:
    """
    Evaluates a DecisionContext and returns a structured Decision.

    The engine is a pure function object: given the same context and policy,
    it always returns the same decision. It has no side effects.

    Decision priority order:
        1. SUCCESS  → CONTINUE
        2. Failure + retries remaining → RETRY
        3. CAPABILITY_UNAVAILABLE or DEPENDENCY_FAILURE → SKIP
        4. All tasks failed or termination condition → TERMINATE
        5. Default → REPLAN (attempt to recover via new tasks)

    Usage::

        engine = DecisionEngine(retry_policy=RetryPolicy())
        decision = engine.make_decision(context)
    """

    def __init__(self, retry_policy: RetryPolicy | None = None) -> None:
        self._retry_policy = retry_policy or RetryPolicy()

    def make_decision(self, context: DecisionContext) -> Decision:
        """
        Produce a Decision based on the provided DecisionContext.

        Args:
            context: Fully populated DecisionContext with task evaluation,
                     attempt count, and graph state snapshot.

        Returns:
            Decision with a DecisionType and human-readable reason.
        """
        evaluation = context.evaluation

        # ── SUCCESS path ──────────────────────────────────────────────────
        if evaluation.is_success:
            return Decision(
                decision_type=DecisionType.CONTINUE,
                reason="Task completed successfully.",
            )

        # ── FAILURE path ──────────────────────────────────────────────────
        category = evaluation.failure_category or FailureCategory.UNKNOWN

        # Categories that should never be retried — skip immediately
        non_retryable = {
            FailureCategory.CAPABILITY_UNAVAILABLE,
            FailureCategory.DEPENDENCY_FAILURE,
            FailureCategory.USER_ERROR,
        }
        if category in non_retryable:
            return Decision(
                decision_type=DecisionType.SKIP,
                reason=(
                    f"Failure category [{category.value}] is non-retryable. "
                    "Skipping task to unblock downstream graph."
                ),
            )

        # Check retry budget
        if self._retry_policy.is_retryable(category, context.attempt_count):
            remaining = self._retry_policy.max_retries_for(category) - context.attempt_count
            return Decision(
                decision_type=DecisionType.RETRY,
                reason=(
                    f"Failure category [{category.value}] is retryable. "
                    f"Attempt {context.attempt_count + 1} of "
                    f"{self._retry_policy.max_retries_for(category) + 1}. "
                    f"{remaining} retries remaining."
                ),
            )

        # Terminate if graph is mostly failed and no pending tasks remain
        if context.pending_count == 0 and context.failed_count > 0:
            return Decision(
                decision_type=DecisionType.TERMINATE,
                reason=(
                    f"Retry budget exhausted for [{category.value}] "
                    "and no pending tasks remain. Terminating execution."
                ),
            )

        # Attempt recovery via replanning for recoverable but exhausted categories
        recoverable_replan = {
            FailureCategory.LLM_FAILURE,
            FailureCategory.VALIDATION_FAILURE,
            FailureCategory.UNKNOWN,
        }
        if category in recoverable_replan:
            return Decision(
                decision_type=DecisionType.REPLAN,
                reason=(
                    f"Retry budget exhausted for [{category.value}]. "
                    "Requesting Supervisor to insert recovery tasks via replanning."
                ),
            )

        # Final fallback: skip
        return Decision(
            decision_type=DecisionType.SKIP,
            reason=(
                f"No valid decision path for [{category.value}] after "
                f"{context.attempt_count} attempt(s). Skipping task."
            ),
        )
