"""Retriever abstract interface."""

from abc import ABC, abstractmethod
from typing import List

from knowledge.documents.base import Document


class BaseRetriever(ABC):
    """Abstract interface for knowledge retrieval."""

    @abstractmethod
    async def retrieve(self, query: str) -> List[Document]:
        """Retrieve relevant documents for query."""
        pass
