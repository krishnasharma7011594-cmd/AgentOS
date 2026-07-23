"""Document indexer interface."""

from abc import ABC, abstractmethod
from typing import List

from knowledge.documents.base import Document


class BaseDocumentIndexer(ABC):
    """Abstract interface for indexing documents."""

    @abstractmethod
    async def index(self, documents: List[Document]) -> None:
        """Index documents into retrieval search indexes."""
        pass
