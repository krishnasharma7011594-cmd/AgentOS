"""
Context Strategy Implementations

Architecture Layer: Core / Context / Strategies
"""

import time
from typing import List

from core.context.strategies.base import ContextStrategy
from core.models.context import (
    ContextItem,
    ContextPriority,
    ContextReason,
    ContextRequest,
    ContextSource,
)
from core.models.memory import MemoryQuery, MemoryRecordType, MemoryResult


class SemanticContextStrategy(ContextStrategy):
    """
    Retrieves general context based on semantic similarity to the goal.
    """

    @property
    def name(self) -> str:
        return "SemanticContextStrategy"

    def build_queries(self, request: ContextRequest) -> List[MemoryQuery]:
        # Perform semantic search using the goal description
        return [
            MemoryQuery(
                text=request.goal_description,
                top_k=5,
                # Note: The ContextResolver will embed the text and pass it to MemoryService.
                # Here we just specify what text to search for.
            )
        ]

    def transform(
        self, request: ContextRequest, results: List[MemoryResult]
    ) -> List[ContextItem]:
        items = []
        now = time.time()
        for res in results:
            # Map memory record type to context source
            source = ContextSource.MEMORY
            if res.record.record_type == MemoryRecordType.KNOWLEDGE:
                source = ContextSource.KNOWLEDGE
            
            items.append(
                ContextItem(
                    content=res.record.content,
                    source=source,
                    priority=ContextPriority.NORMAL,
                    reason=ContextReason(
                        strategy_name=self.name,
                        explanation="Semantically related to the current goal.",
                    ),
                    relevance_score=res.relevance_score,
                    memory_id=res.record.id,
                    collection=res.record.metadata.attributes.get("_collection"),
                    retrieval_strategy=self.name,
                    retrieval_timestamp=now,
                )
            )
        return items


class ReflectionContextStrategy(ContextStrategy):
    """
    Retrieves past reflections related to the current execution.
    Prioritizes reflections highly since they represent learned lessons.
    """

    @property
    def name(self) -> str:
        return "ReflectionContextStrategy"

    def build_queries(self, request: ContextRequest) -> List[MemoryQuery]:
        queries = []
        # If we have a specific goal_id, fetch reflections for it (useful during retry/replanning).
        if request.goal_id:
            queries.append(
                MemoryQuery(
                    record_types=[MemoryRecordType.REFLECTION],
                    goal_id=request.goal_id,
                    top_k=3,
                )
            )
        # Also fetch semantic matches for reflections
        queries.append(
            MemoryQuery(
                text=request.goal_description,
                record_types=[MemoryRecordType.REFLECTION],
                top_k=3,
            )
        )
        return queries

    def transform(
        self, request: ContextRequest, results: List[MemoryResult]
    ) -> List[ContextItem]:
        items = []
        now = time.time()
        for res in results:
            items.append(
                ContextItem(
                    content=res.record.content,
                    source=ContextSource.REFLECTION,
                    priority=ContextPriority.CRITICAL,
                    reason=ContextReason(
                        strategy_name=self.name,
                        explanation="Historical reflection matching current goal.",
                    ),
                    relevance_score=res.relevance_score,
                    memory_id=res.record.id,
                    collection=res.record.metadata.attributes.get("_collection"),
                    retrieval_strategy=self.name,
                    retrieval_timestamp=now,
                )
            )
        return items


class ExecutionHistoryStrategy(ContextStrategy):
    """
    Retrieves previous execution summaries related to this goal.
    """

    @property
    def name(self) -> str:
        return "ExecutionHistoryStrategy"

    def build_queries(self, request: ContextRequest) -> List[MemoryQuery]:
        if not request.goal_id:
            return []
        return [
            MemoryQuery(
                goal_id=request.goal_id,
                record_types=[MemoryRecordType.EXECUTION],
                top_k=5,
            )
        ]

    def transform(
        self, request: ContextRequest, results: List[MemoryResult]
    ) -> List[ContextItem]:
        items = []
        now = time.time()
        for res in results:
            items.append(
                ContextItem(
                    content=res.record.content,
                    source=ContextSource.EXECUTION,
                    priority=ContextPriority.HIGH,
                    reason=ContextReason(
                        strategy_name=self.name,
                        explanation="Prior execution attempt for this goal.",
                    ),
                    relevance_score=res.relevance_score,
                    memory_id=res.record.id,
                    collection=res.record.metadata.attributes.get("_collection"),
                    retrieval_strategy=self.name,
                    retrieval_timestamp=now,
                )
            )
        return items


class KnowledgeContextStrategy(ContextStrategy):
    """
    Specifically targets knowledge base collections for factual information.
    """

    @property
    def name(self) -> str:
        return "KnowledgeContextStrategy"

    def build_queries(self, request: ContextRequest) -> List[MemoryQuery]:
        queries = [
            MemoryQuery(
                text=request.goal_description,
                record_types=[MemoryRecordType.KNOWLEDGE],
                top_k=5,
            )
        ]
        if request.task_description:
            queries.append(
                MemoryQuery(
                    text=request.task_description,
                    record_types=[MemoryRecordType.KNOWLEDGE],
                    top_k=3,
                )
            )
        return queries

    def transform(
        self, request: ContextRequest, results: List[MemoryResult]
    ) -> List[ContextItem]:
        items = []
        now = time.time()
        for res in results:
            items.append(
                ContextItem(
                    content=res.record.content,
                    source=ContextSource.KNOWLEDGE,
                    priority=ContextPriority.NORMAL,
                    reason=ContextReason(
                        strategy_name=self.name,
                        explanation="Factual knowledge relevant to the task/goal.",
                    ),
                    relevance_score=res.relevance_score,
                    memory_id=res.record.id,
                    collection=res.record.metadata.attributes.get("_collection"),
                    retrieval_strategy=self.name,
                    retrieval_timestamp=now,
                )
            )
        return items
