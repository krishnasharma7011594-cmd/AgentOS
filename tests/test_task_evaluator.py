"""Tests for TaskEvaluator — failure classification and success detection (Phase 5)."""

import uuid

import pytest

from core.models.domain import FailureCategory, Task, TaskResult, TaskStatus
from supervisor.evaluator import TaskEvaluator


def _task(capability: str = "web_research") -> Task:
    gid = str(uuid.uuid4())
    return Task(
        id=str(uuid.uuid4()),
        goal_id=gid,
        name="Test task",
        description="Perform research",
        required_capability=capability,
    )


def _result(
    task_id: str, status: TaskStatus, error: str | None = None, summary: str = "Done."
) -> TaskResult:
    return TaskResult(
        task_id=task_id,
        agent_id="agent1",
        status=status,
        summary=summary,
        error=error,
    )


@pytest.fixture
def evaluator() -> TaskEvaluator:
    return TaskEvaluator()


class TestTaskEvaluatorSuccess:
    def test_success_result_is_classified_correctly(self, evaluator: TaskEvaluator) -> None:
        task = _task()
        result = _result(task.id, TaskStatus.SUCCESS, summary="Detailed research result here.")
        ev = evaluator.evaluate(task, result)
        assert ev.is_success is True
        assert ev.failure_category is None
        assert ev.is_partial is False

    def test_short_summary_flags_partial(self, evaluator: TaskEvaluator) -> None:
        task = _task()
        result = _result(task.id, TaskStatus.SUCCESS, summary="ok")
        ev = evaluator.evaluate(task, result)
        assert ev.is_success is True
        assert ev.is_partial is True


class TestTaskEvaluatorFailureClassification:
    @pytest.mark.parametrize(
        "error,expected",
        [
            ("connection timeout exceeded", FailureCategory.TIMEOUT),
            ("timed out waiting for response", FailureCategory.TIMEOUT),
            ("LLM provider error", FailureCategory.LLM_FAILURE),
            ("Gemini generation failed", FailureCategory.LLM_FAILURE),
            ("tool failed to execute web search", FailureCategory.TOOL_FAILURE),
            ("validation error: invalid schema", FailureCategory.VALIDATION_FAILURE),
            ("capability not found for agent", FailureCategory.CAPABILITY_UNAVAILABLE),
            ("no agent available for capability", FailureCategory.CAPABILITY_UNAVAILABLE),
            ("upstream dependency task failed", FailureCategory.DEPENDENCY_FAILURE),
            ("something completely unexpected happened", FailureCategory.UNKNOWN),
        ],
    )
    def test_failure_classification(
        self, evaluator: TaskEvaluator, error: str, expected: FailureCategory
    ) -> None:
        task = _task()
        result = _result(task.id, TaskStatus.FAILED, error=error, summary="")
        ev = evaluator.evaluate(task, result)
        assert ev.is_success is False
        assert ev.failure_category == expected

    def test_failed_result_has_downstream_impact(self, evaluator: TaskEvaluator) -> None:
        task = _task()
        result = _result(task.id, TaskStatus.FAILED, error="timeout")
        ev = evaluator.evaluate(task, result)
        assert ev.downstream_impact != ""

    def test_notes_contain_category(self, evaluator: TaskEvaluator) -> None:
        task = _task()
        result = _result(task.id, TaskStatus.FAILED, error="timeout exceeded")
        ev = evaluator.evaluate(task, result)
        assert "timeout" in ev.notes.lower()
