"""
Context Ranker

Ranks, normalizes, and deduplicates ContextItems.
Prioritizes critical sources like Execution History and Reflections.

Architecture Layer: Core / Context
"""

from typing import List, Set

from core.models.context import ContextItem, ContextPriority


class ContextRanker:
    """
    Ranks ContextItems deterministically.
    """

    def __init__(self) -> None:
        self._priority_weights = {
            ContextPriority.LOW: 0.5,
            ContextPriority.NORMAL: 1.0,
            ContextPriority.HIGH: 1.5,
            ContextPriority.CRITICAL: 2.0,
        }

    def rank(self, items: List[ContextItem]) -> List[ContextItem]:
        """
        Deduplicates by memory_id, scores them using priority weight * relevance_score,
        and sorts them descending.
        """
        if not items:
            return []

        # Deduplicate
        unique_items: List[ContextItem] = []
        seen_memory_ids: Set[str] = set()

        for item in items:
            if item.memory_id and item.memory_id in seen_memory_ids:
                continue
            if item.memory_id:
                seen_memory_ids.add(item.memory_id)
            unique_items.append(item)

        # Sort
        # Score = relevance_score * priority_weight
        # We also use retrieval_timestamp as a tie-breaker (newer is better)
        def sort_key(itm: ContextItem) -> tuple:
            weight = self._priority_weights.get(itm.priority, 1.0)
            score = itm.relevance_score * weight
            return (score, itm.retrieval_timestamp)

        unique_items.sort(key=sort_key, reverse=True)

        return unique_items
