from typing import Dict, List, Optional

from core.exceptions.base import CapabilityNotFoundError
from core.logging.logger import logger
from core.models.capability import CapabilityDescriptor


class CapabilityRegistry:
    """
    Registry for storing and managing logical capabilities, versions, metadata, and policies.
    This registry does NOT know about concrete tool implementations, it only tracks what
    capabilities exist in the system and their requirements.
    """

    def __init__(self) -> None:
        # map: capability_name -> CapabilityDescriptor
        self._capabilities: Dict[str, CapabilityDescriptor] = {}

    def register(self, descriptor: CapabilityDescriptor) -> None:
        """Register a new capability descriptor."""
        self._capabilities[descriptor.metadata.name] = descriptor
        logger.info(
            "capability_registered",
            name=descriptor.metadata.name,
            version=str(descriptor.metadata.version),
        )

    def unregister(self, name: str) -> None:
        """Remove a capability descriptor."""
        if name in self._capabilities:
            del self._capabilities[name]
            logger.info("capability_unregistered", name=name)

    def get_descriptor(self, name: str) -> CapabilityDescriptor:
        """Get a capability descriptor by name, raising an error if missing."""
        desc = self._capabilities.get(name)
        if not desc:
            raise CapabilityNotFoundError(f"Capability '{name}' not found in registry.")
        return desc

    def get(self, name: str) -> Optional[CapabilityDescriptor]:
        """Safe version of get_descriptor returning None if missing."""
        return self._capabilities.get(name)

    def list_capabilities(self) -> List[CapabilityDescriptor]:
        """Return all registered capabilities."""
        return list(self._capabilities.values())
