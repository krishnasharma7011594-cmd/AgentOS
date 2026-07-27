"""
TaskEvaluator

Inspects a TaskResult to produce a structured TaskEvaluation, classifying
failure modes and assessing downstream impact.

The evaluator is a pure function: given a Task and a TaskResult, it always
returns the same TaskEvaluation without side effects.

Architecture Layer: Supervisor / Evaluation (Phase 5)
"""

from core.models.domain import FailureCategory, Task, TaskEvaluation, TaskResult, TaskStatus

# Keywords used to infer failure categories from error messages.
_TIMEOUT_KEYWORDS = ("timeout", "timed out", "time limit", "deadline exceeded")
_LLM_KEYWORDS = (
    "llm",
    "language model",
    "provider",
    "gemini",
    "groq",
    "openai",
    "generation failed",
)
_TOOL_KEYWORDS = ("tool", "web search", "execution error", "tool failed", "duckduckgo")
_VALIDATION_KEYWORDS = ("validation", "invalid", "schema", "format", "parse error")
_CAPABILITY_KEYWORDS = ("capability", "no agent", "not found", "unavailable", "unsupported")
_DEPENDENCY_KEYWORDS = ("dependency", "upstream", "required task", "depends on")
_USER_KEYWORDS = ("user error", "bad request", "invalid input")


def _classify_failure(error: str) -> FailureCategory:
    """Classify a failure message into a FailureCategory."""
    lower = error.lower()
    if any(kw in lower for kw in _TIMEOUT_KEYWORDS):
        return FailureCategory.TIMEOUT
    if any(kw in lower for kw in _CAPABILITY_KEYWORDS):
        return FailureCategory.CAPABILITY_UNAVAILABLE
    if any(kw in lower for kw in _DEPENDENCY_KEYWORDS):
        return FailureCategory.DEPENDENCY_FAILURE
    if any(kw in lower for kw in _VALIDATION_KEYWORDS):
        return FailureCategory.VALIDATION_FAILURE
    if any(kw in lower for kw in _LLM_KEYWORDS):
        return FailureCategory.LLM_FAILURE
    if any(kw in lower for kw in _TOOL_KEYWORDS):
        return FailureCategory.TOOL_FAILURE
    if any(kw in lower for kw in _USER_KEYWORDS):
        return FailureCategory.USER_ERROR
    return FailureCategory.UNKNOWN


class TaskEvaluator:
    """
    Produces structured TaskEvaluation objects from raw TaskResult data.

    The evaluator inspects status, error messages, and summary quality to
    classify outcomes. It never mutates state or emits events.

    Usage::

        evaluator = TaskEvaluator()
        evaluation = evaluator.evaluate(task, result)
    """

    def evaluate(self, task: Task, result: TaskResult) -> TaskEvaluation:
        """
        Evaluate a completed TaskResult for a given Task.

        Args:
            task:   The Task that was executed.
            result: The TaskResult returned by the executing agent.

        Returns:
            TaskEvaluation with structured success/failure information.
        """
        is_success = result.status == TaskStatus.SUCCESS

        if is_success:
            # Evaluate partial success: task succeeded but summary is suspiciously short
            is_partial = len(result.summary.strip()) < 20
            return TaskEvaluation(
                task_id=task.id,
                is_success=True,
                is_partial=is_partial,
                failure_category=None,
                downstream_impact="",
                notes="Partial output detected — summary unusually short." if is_partial else "",
            )

        # Task failed — classify and assess downstream impact
        error_text = result.error or result.summary or "unknown error"
        category = _classify_failure(error_text)

        downstream_impact = (
            f"Task '{task.name}' failed. "
            f"{len(task.dependencies)} upstream dependencies were satisfied; "
            "downstream tasks depending on this task will be blocked or skipped."
            if not is_success
            else ""
        )

        notes = f"Failure classified as [{category.value}]. Error: {error_text[:200]}"

        return TaskEvaluation(
            task_id=task.id,
            is_success=False,
            is_partial=False,
            failure_category=category,
            downstream_impact=downstream_impact,
            notes=notes,
        )
