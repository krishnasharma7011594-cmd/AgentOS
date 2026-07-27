"""Integration tests for ReflectionEngine (Phase 6)."""

from core.models.domain import ExecutionMetrics, ExecutionReport
from supervisor.reflection.engine import ReflectionEngine


def test_reflection_engine_integration() -> None:
    engine = ReflectionEngine()
    report = ExecutionReport(
        goal_id="g1",
        goal_description="test reflection",
        overall_status="success",
        metrics=ExecutionMetrics(
            total_tasks=2,
            completed_tasks=2,
        ),
        final_response="Success",
    )

    reflection = engine.reflect(report)

    # Validate high-level structure
    assert reflection.reflection_version == "1.0"
    assert reflection.execution_summary.startswith("Execution completed with status 'success'")

    # Check default metrics (from perfect execution)
    assert reflection.scores.overall_score == 100
    assert reflection.metrics.reflection_duration_ms >= 0
    assert reflection.metrics.observation_count >= 1  # Should catch perfect execution
    assert "No retries were necessary" in reflection.retry_analysis
    assert "Original plan was stable" in reflection.replanning_analysis
