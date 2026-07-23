"""Vectorstore abstract interface."""

from abc import ABC, abstractmethod
from typing import List

from knowledge.documents.base import Document


class BaseVectorStore(ABC):
    """Abstract vector database wrapper interface."""

    @abstractmethod
    async def add_documents(self, documents: List[Document]) -> None:
        """Insert documents into vectorstore."""
        pass

    @abstractmethod
    async def similarity_search(self, query: str, k: int = 4) -> List[Document]:
        """Perform similarity search for query string."""
        pass
