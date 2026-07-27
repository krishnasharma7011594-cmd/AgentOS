"""Tests for RecommendationEngine (Phase 6)."""

from core.models.reflection import (
    ExecutionReview,
    ReflectionCategory,
    ReflectionObservation,
    ReflectionSeverity,
)
from supervisor.reflection._recommender import RecommendationEngine


def test_retry_recommendation() -> None:
    recommender = RecommendationEngine()
    obs = ReflectionObservation(
        category=ReflectionCategory.RETRY,
        severity=ReflectionSeverity.HIGH,
        description="High churn",
        evidence="4 retries",
    )
    review = ExecutionReview(goal_id="g1", observations=[obs])

    recs = recommender.recommend(review)
    assert len(recs) == 1
    assert recs[0].category == ReflectionCategory.RETRY
    assert recs[0].observation_id == obs.id


def test_no_info_recommendation() -> None:
    recommender = RecommendationEngine()
    obs = ReflectionObservation(
        category=ReflectionCategory.PLANNING,
        severity=ReflectionSeverity.INFO,
        description="Perfect",
        evidence="None",
    )
    review = ExecutionReview(goal_id="g1", observations=[obs])

    recs = recommender.recommend(review)
    assert len(recs) == 0
