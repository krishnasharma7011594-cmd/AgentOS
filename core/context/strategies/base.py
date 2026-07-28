"""
Context Strategy Base Interface

Architecture Layer: Core / Context / Strategies
"""

from abc import ABC, abstractmethod
from typing import List

from core.models.context import ContextItem, ContextRequest
from core.models.memory import MemoryQuery, MemoryResult


class ContextStrategy(ABC):
    """
    Abstract interface for Context Strategies.

    Strategies are completely decoupled from storage (MemoryService).
    They follow a two-step lifecycle orchestrated by the ContextResolver:
    1. build_queries: Strategy examines the ContextRequest and produces MemoryQueries.
    2. transform: Resolver executes queries against MemoryService and passes
       the MemoryResults back to the strategy, which converts them into ContextItems.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """The unique name of this strategy (e.g., 'SemanticContextStrategy')."""
        pass

    @abstractmethod
    def build_queries(self, request: ContextRequest) -> List[MemoryQuery]:
        """
        Generate memory queries based on the execution context.
        Return an empty list if this strategy decides it has nothing to query.
        """
        pass

    @abstractmethod
    def transform(self, request: ContextRequest, results: List[MemoryResult]) -> List[ContextItem]:
        """
        Transform raw memory retrieval results into structured ContextItems.
        The strategy is responsible for setting the priority, source, and reason.
        """
        pass
