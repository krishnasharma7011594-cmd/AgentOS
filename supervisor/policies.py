"""
Supervisor Policies

Defines configurable policy rules consumed by the DecisionEngine to determine
which failure categories are retryable and how many times each may be retried.

Policies are data objects — they hold configuration, not behaviour.

Architecture Layer: Supervisor / Policies (Phase 5)
"""

from dataclasses import dataclass, field

from core.models.domain import FailureCategory


@dataclass
class RetryPolicy:
    """
    Configures retry behaviour per FailureCategory.

    Attributes:
        max_retries_by_category: Maps each FailureCategory to the maximum
            number of allowed retry attempts. A value of 0 means no retries.
        default_max_retries:     Fallback for categories not explicitly listed.
    """

    max_retries_by_category: dict[FailureCategory, int] = field(
        default_factory=lambda: {
            FailureCategory.TIMEOUT: 3,
            FailureCategory.LLM_FAILURE: 2,
            FailureCategory.TOOL_FAILURE: 2,
            FailureCategory.VALIDATION_FAILURE: 1,
            FailureCategory.DEPENDENCY_FAILURE: 0,
            FailureCategory.CAPABILITY_UNAVAILABLE: 0,
            FailureCategory.USER_ERROR: 0,
            FailureCategory.UNKNOWN: 1,
        }
    )
    default_max_retries: int = 1

    def max_retries_for(self, category: FailureCategory) -> int:
        """Return the maximum retry count for a given FailureCategory."""
        return self.max_retries_by_category.get(category, self.default_max_retries)

    def is_retryable(self, category: FailureCategory, attempt_count: int) -> bool:
        """
        Return True when the failure category permits at least one more retry.

        Args:
            category:      The FailureCategory to check.
            attempt_count: Number of prior attempts (0 means first attempt just failed).
        """
        return attempt_count < self.max_retries_for(category)
