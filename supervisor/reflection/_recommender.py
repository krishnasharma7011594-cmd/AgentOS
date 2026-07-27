"""
Recommendation Engine (Internal)

Takes an ExecutionReview and deterministically maps its observations to
ReflectionRecommendations.

Recommendations are advisory and do not automatically alter execution state.

Architecture Layer: Supervisor / Reflection
"""

from typing import List

from core.models.reflection import (
    ExecutionReview,
    ReflectionCategory,
    ReflectionRecommendation,
    ReflectionSeverity,
)


class RecommendationEngine:
    """
    Internal engine for mapping observations to actionable recommendations.
    """

    def recommend(self, review: ExecutionReview) -> List[ReflectionRecommendation]:
        """
        Generate recommendations based on structured observations.
        """
        recommendations: List[ReflectionRecommendation] = []

        for obs in review.observations:
            if obs.category == ReflectionCategory.RETRY and obs.severity in (
                ReflectionSeverity.MEDIUM,
                ReflectionSeverity.HIGH,
            ):
                recommendations.append(
                    ReflectionRecommendation(
                        observation_id=obs.id,
                        category=ReflectionCategory.RETRY,
                        evidence=obs.evidence,
                        explanation="Excessive retries increase latency and token costs.",
                        suggested_improvement="Review agent prompt constraints or tool implementations to reduce intermittent failures.",
                    )
                )

            elif obs.category == ReflectionCategory.CAPABILITY_SELECTION:
                recommendations.append(
                    ReflectionRecommendation(
                        observation_id=obs.id,
                        category=ReflectionCategory.CAPABILITY_SELECTION,
                        evidence=obs.evidence,
                        explanation="The planner hallucinated or incorrectly inferred a required capability.",
                        suggested_improvement="Update planner keyword mappings or capability definitions in AgentMetadata.",
                    )
                )

            elif (
                obs.category == ReflectionCategory.EXECUTION
                and obs.severity == ReflectionSeverity.HIGH
            ):
                recommendations.append(
                    ReflectionRecommendation(
                        observation_id=obs.id,
                        category=ReflectionCategory.EXECUTION,
                        evidence=obs.evidence,
                        explanation="The goal could not be fully achieved with the current plan.",
                        suggested_improvement="Consider breaking the goal down into smaller sub-goals or reviewing task dependencies.",
                    )
                )

            # Note: We do not generate recommendations for INFO severity,
            # as they typically represent expected or ideal behavior.

        return recommendations
