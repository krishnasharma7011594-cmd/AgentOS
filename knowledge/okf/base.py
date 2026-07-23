"""Organizational Knowledge Framework (OKF) interface."""

from abc import ABC, abstractmethod


class BaseOKFManager(ABC):
    """Abstract interface for Organizational Knowledge Framework management."""

    @abstractmethod
    async def sync_knowledge(self) -> None:
        """Synchronize organizational knowledge structures."""
        pass
