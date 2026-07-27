"""Tests for DecisionEngine — pure decision logic (Phase 5)."""

import pytest

from core.models.domain import (
    DecisionContext,
    DecisionType,
    FailureCategory,
    TaskEvaluation,
)
from supervisor.decision_engine import DecisionEngine
from supervisor.policies import RetryPolicy


def _success_eval(task_id: str = "t1") -> TaskEvaluation:
    return TaskEvaluation(task_id=task_id, is_success=True)


def _fail_eval(
    task_id: str = "t1", category: FailureCategory = FailureCategory.TIMEOUT
) -> TaskEvaluation:
    return TaskEvaluation(task_id=task_id, is_success=False, failure_category=category)


def _ctx(
    evaluation: TaskEvaluation,
    attempt_count: int = 0,
    pending_count: int = 1,
    failed_count: int = 0,
) -> DecisionContext:
    return DecisionContext(
        task_id=evaluation.task_id,
        evaluation=evaluation,
        attempt_count=attempt_count,
        pending_count=pending_count,
        failed_count=failed_count,
    )


@pytest.fixture
def engine() -> DecisionEngine:
    return DecisionEngine(retry_policy=RetryPolicy())


class TestDecisionEngineSuccess:
    def test_success_returns_continue(self, engine: DecisionEngine) -> None:
        decision = engine.make_decision(_ctx(_success_eval()))
        assert decision.decision_type == DecisionType.CONTINUE

    def test_continue_has_reason(self, engine: DecisionEngine) -> None:
        decision = engine.make_decision(_ctx(_success_eval()))
        assert len(decision.reason) > 0


class TestDecisionEngineRetry:
    def test_timeout_first_attempt_returns_retry(self, engine: DecisionEngine) -> None:
        ev = _fail_eval(category=FailureCategory.TIMEOUT)
        decision = engine.make_decision(_ctx(ev, attempt_count=0))
        assert decision.decision_type == DecisionType.RETRY

    def test_llm_failure_first_attempt_returns_retry(self, engine: DecisionEngine) -> None:
        ev = _fail_eval(category=FailureCategory.LLM_FAILURE)
        decision = engine.make_decision(_ctx(ev, attempt_count=0))
        assert decision.decision_type == DecisionType.RETRY

    def test_tool_failure_first_attempt_returns_retry(self, engine: DecisionEngine) -> None:
        ev = _fail_eval(category=FailureCategory.TOOL_FAILURE)
        decision = engine.make_decision(_ctx(ev, attempt_count=0))
        assert decision.decision_type == DecisionType.RETRY

    def test_retry_reason_contains_attempt_info(self, engine: DecisionEngine) -> None:
        ev = _fail_eval(category=FailureCategory.TIMEOUT)
        decision = engine.make_decision(_ctx(ev, attempt_count=1))
        assert "attempt" in decision.reason.lower() or "retr" in decision.reason.lower()


class TestDecisionEngineSkip:
    def test_capability_unavailable_returns_skip(self, engine: DecisionEngine) -> None:
        ev = _fail_eval(category=FailureCategory.CAPABILITY_UNAVAILABLE)
        decision = engine.make_decision(_ctx(ev))
        assert decision.decision_type == DecisionType.SKIP

    def test_dependency_failure_returns_skip(self, engine: DecisionEngine) -> None:
        ev = _fail_eval(category=FailureCategory.DEPENDENCY_FAILURE)
        decision = engine.make_decision(_ctx(ev))
        assert decision.decision_type == DecisionType.SKIP

    def test_user_error_returns_skip(self, engine: DecisionEngine) -> None:
        ev = _fail_eval(category=FailureCategory.USER_ERROR)
        decision = engine.make_decision(_ctx(ev))
        assert decision.decision_type == DecisionType.SKIP


class TestDecisionEngineRetryExhaustion:
    def test_timeout_budget_exhausted_returns_replan_or_terminate(
        self, engine: DecisionEngine
    ) -> None:
        ev = _fail_eval(category=FailureCategory.TIMEOUT)
        # Default policy: TIMEOUT max 3 retries — exhaust them
        decision = engine.make_decision(_ctx(ev, attempt_count=3, pending_count=2))
        assert decision.decision_type in (
            DecisionType.REPLAN,
            DecisionType.TERMINATE,
            DecisionType.SKIP,
        )

    def test_custom_policy_no_retries(self) -> None:
        policy = RetryPolicy(max_retries_by_category={FailureCategory.TIMEOUT: 0})
        engine = DecisionEngine(retry_policy=policy)
        ev = _fail_eval(category=FailureCategory.TIMEOUT)
        decision = engine.make_decision(_ctx(ev, attempt_count=0))
        # With 0 retries allowed, should NOT be RETRY
        assert decision.decision_type != DecisionType.RETRY


class TestDecisionEnginePurity:
    def test_engine_does_not_mutate_context(self, engine: DecisionEngine) -> None:
        ev = _success_eval()
        ctx = _ctx(ev, attempt_count=2)
        engine.make_decision(ctx)
        # Context must be unchanged
        assert ctx.attempt_count == 2
        assert ctx.evaluation.is_success is True
