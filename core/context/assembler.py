"""
Context Assembler

Merges ranked items and enforces assembly policies to produce
an immutable ContextBundle.

Architecture Layer: Core / Context
"""

from typing import List

from core.models.context import (
    ContextAssemblyPolicy,
    ContextBundle,
    ContextItem,
    ContextMetrics,
    ContextScope,
)


class ContextAssembler:
    """
    Enforces ContextAssemblyPolicy on a ranked list of items and produces
    the final immutable ContextBundle.
    """

    def __init__(self, default_policy: ContextAssemblyPolicy) -> None:
        self._default_policy = default_policy

    def assemble(
        self,
        ranked_items: List[ContextItem],
        scope: ContextScope,
        metrics: ContextMetrics,
        override_policy: ContextAssemblyPolicy | None = None,
    ) -> ContextBundle:
        """
        Enforce max_items and min_relevance_score, then construct the bundle.
        """
        policy = override_policy or self._default_policy

        final_items: List[ContextItem] = []
        discarded_count = metrics.items_discarded

        for item in ranked_items:
            if len(final_items) >= policy.max_items:
                discarded_count += 1
                continue

            if item.relevance_score < policy.min_relevance_score:
                discarded_count += 1
                continue

            final_items.append(item)

        metrics.items_discarded = discarded_count

        return ContextBundle(
            items=final_items,
            scope=scope,
            metrics=metrics,
        )
