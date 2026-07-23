"""Document ingestion interface."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List

from pydantic import BaseModel, Field


class Document(BaseModel):
    """Document data structure."""

    id: str = Field(..., description="Document ID")
    content: str = Field(..., description="Text content")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class BaseDocumentLoader(ABC):
    """Abstract interface for loading external documents."""

    @abstractmethod
    async def load(self, source_path: str) -> List[Document]:
        """Load documents from target source."""
        pass
