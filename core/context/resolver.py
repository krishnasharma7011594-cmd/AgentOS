"""
Context Resolver

Selects and coordinates context retrieval strategies. Fetches raw records
from MemoryService and passes them back to strategies for transformation.

Architecture Layer: Core / Context
"""

from typing import List, Sequence

from core.context.strategies.base import ContextStrategy
from core.memory.service import MemoryService
from core.models.context import ContextItem, ContextRequest


class ContextResolver:
    """
    Coordinates context retrieval.
    Decouples ContextEngine from Strategy execution logic.
    """

    def __init__(
        self,
        memory_service: MemoryService,
        strategies: Sequence[ContextStrategy],
    ) -> None:
        self._memory = memory_service
        self._strategies = list(strategies)

    def resolve(self, request: ContextRequest) -> List[ContextItem]:
        """
        Execute all registered strategies.
        For each strategy:
        1. Ask for MemoryQueries.
        2. Execute the queries against MemoryService
           (hybrid search if text provided, else metadata).
        3. Pass MemoryResults back to strategy to transform into ContextItems.
        """
        all_items: List[ContextItem] = []

        for strategy in self._strategies:
            queries = strategy.build_queries(request)
            if not queries:
                continue

            # Execute queries
            strategy_results = []
            for query in queries:
                # Apply ContextSelectionPolicy filtering
                if request.selection_policy:
                    # NOTE: Further implementation can filter MemoryQuery here
                    # based on allowed sources/collections.
                    # For now, collection filters are deferred to query attributes.
                    # (A full implementation would map policies strictly to queries.)
                    pass

                # If it's a semantic query
                if query.text:
                    results = self._memory.search(query.text, top_k=query.top_k)
                    # Filter results by the query attributes if provided
                    filtered = []
                    for r in results:
                        match = True
                        if query.goal_id and r.record.metadata.goal_id != query.goal_id:
                            match = False
                        if query.record_types and r.record.record_type not in query.record_types:
                            match = False
                        if match:
                            filtered.append(r)
                    strategy_results.extend(filtered)
                else:
                    # Just metadata query
                    results = self._memory.retrieve_by_metadata(query)
                    strategy_results.extend(results)

            # Deduplicate intermediate MemoryResults by ID
            # to avoid redundant items from the same strategy.
            unique_results = []
            seen = set()
            for r in strategy_results:
                if r.record.id not in seen:
                    seen.add(r.record.id)
                    unique_results.append(r)

            # Transform
            items = strategy.transform(request, unique_results)
            all_items.extend(items)

        return all_items
