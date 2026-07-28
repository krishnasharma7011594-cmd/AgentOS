"""
Context Engine

The single public entry point for the Context subsystem.
Orchestrates the ContextResolver, ContextRanker, and ContextAssembler.

Architecture Layer: Core / Context
"""

import time

from core.context.assembler import ContextAssembler
from core.context.ranker import ContextRanker
from core.context.resolver import ContextResolver
from core.logging.logger import logger
from core.models.context import (
    ContextBundle,
    ContextMetrics,
    ContextRequest,
)


class ContextEngine:
    """
    Intelligent Context Engine (Phase 8).

    Generates structured, execution-aware knowledge for planners, supervisors,
    and agents. Consumes MemoryService but never mutates it.
    """

    def __init__(
        self,
        resolver: ContextResolver,
        ranker: ContextRanker,
        assembler: ContextAssembler,
    ) -> None:
        self._resolver = resolver
        self._ranker = ranker
        self._assembler = assembler

    def build_context(self, request: ContextRequest) -> ContextBundle:
        """
        Orchestrate context generation based on the request.

        1. Resolve: Fetch and transform records via strategies.
        2. Rank: Deduplicate and score ContextItems.
        3. Assemble: Enforce policies and build immutable ContextBundle.
        """
        t0 = time.monotonic()
        metrics = ContextMetrics()

        # 1. Resolve
        logger.debug(
            "ContextEngine: Resolving context",
            goal_id=request.goal_id,
            scope=request.scope.value,
        )
        raw_items = self._resolver.resolve(request)
        metrics.items_retrieved = len(raw_items)

        # 2. Rank
        ranked_items = self._ranker.rank(raw_items)

        # 3. Assemble
        bundle = self._assembler.assemble(
            ranked_items=ranked_items,
            scope=request.scope,
            metrics=metrics,
            override_policy=request.assembly_policy,
        )

        metrics.generation_latency_ms = (time.monotonic() - t0) * 1000

        logger.info(
            "ContextEngine: Built ContextBundle",
            goal_id=request.goal_id,
            scope=request.scope.value,
            items_included=len(bundle.items),
            latency_ms=round(metrics.generation_latency_ms, 2),
        )

        return bundle
