"""
Reflection Engine

Public entry point to the Reflection subsystem.
Analyzes completed executions to generate structured, explainable feedback.
Completely independent from execution — it never mutates state or invokes agents.

Architecture Layer: Supervisor / Reflection
"""

import time

from core.logging.logger import logger
from core.models.domain import DecisionType, ExecutionReport
from core.models.reflection import ReflectionMetrics, ReflectionReport
from supervisor.reflection._recommender import RecommendationEngine
from supervisor.reflection._reviewer import ExecutionReviewer
from supervisor.reflection._scorer import ReflectionScorer


class ReflectionEngine:
    """
    Public API for analyzing completed executions.
    """

    def __init__(self) -> None:
        self._reviewer = ExecutionReviewer()
        self._recommender = RecommendationEngine()
        self._scorer = ReflectionScorer()
        logger.info("ReflectionEngine: initialized (Phase 6 — Reflective)")

    def reflect(self, report: ExecutionReport) -> ReflectionReport:
        """
        Produce a ReflectionReport from a completed ExecutionReport.

        Args:
            report: The final report of a completed execution.

        Returns:
            ReflectionReport: Structured analysis, recommendations, and scores.
        """
        start_time = time.monotonic()
        logger.info(
            "ReflectionEngine: starting reflection",
            goal_id=report.goal_id,
            status=report.overall_status,
        )

        # 1. Review
        review = self._reviewer.review(report)

        # 2. Recommend
        recommendations = self._recommender.recommend(review)

        # 3. Score
        scores = self._scorer.score(report, review)

        # 4. Synthesize Analyses
        decision_log = report.metrics.decision_log
        retries = sum(1 for d in decision_log if d.decision.decision_type == DecisionType.RETRY)
        replans = sum(1 for d in decision_log if d.decision.decision_type == DecisionType.REPLAN)

        retry_analysis = f"Total retries: {retries}. "
        if retries > 0:
            retry_analysis += "Retry mechanism was engaged."
        else:
            retry_analysis += "No retries were necessary."

        replanning_analysis = f"Total replans: {replans}. "
        if replans > 0:
            replanning_analysis += "Graph was dynamically mutated."
        else:
            replanning_analysis += "Original plan was stable."

        decision_summary = f"Total supervisor decisions: {len(decision_log)}."

        # 5. Measure
        duration_ms = (time.monotonic() - start_time) * 1000.0
        metrics = ReflectionMetrics(
            reflection_duration_ms=round(duration_ms, 2),
            observation_count=len(review.observations),
            recommendation_count=len(recommendations),
            average_score=scores.overall_score,
        )

        # 6. Assemble
        reflection_report = ReflectionReport(
            reflection_version="1.0",
            execution_summary=(
                f"Execution completed with status '{report.overall_status}' "
                f"in {report.metrics.execution_time_ms}ms."
            ),
            observations=review.observations,
            recommendations=recommendations,
            scores=scores,
            metrics=metrics,
            decision_summary=decision_summary,
            retry_analysis=retry_analysis,
            replanning_analysis=replanning_analysis,
        )

        logger.info(
            "ReflectionEngine: reflection complete",
            goal_id=report.goal_id,
            overall_score=scores.overall_score,
            observations=metrics.observation_count,
            recommendations=metrics.recommendation_count,
            duration_ms=metrics.reflection_duration_ms,
        )

        return reflection_report
