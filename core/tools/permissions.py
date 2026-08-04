from typing import List, Set

from core.logging.logger import logger
from core.models.capability import CapabilityPermission


class PermissionDeniedError(Exception):
    """Raised when an agent lacks required permissions."""

    pass


class PermissionManager:
    """
    Validates if the current agent/context holds the permissions required
    to execute a capability.
    """

    def __init__(self) -> None:
        # map: agent_id -> set of permission strings
        self._granted_permissions: dict[str, Set[str]] = {}

    def grant_permission(self, agent_id: str, permission: CapabilityPermission) -> None:
        """Grant a specific permission to an agent."""
        if agent_id not in self._granted_permissions:
            self._granted_permissions[agent_id] = set()
        self._granted_permissions[agent_id].add(str(permission))
        logger.info("permission_granted", agent=agent_id, permission=str(permission))

    def revoke_permission(self, agent_id: str, permission: CapabilityPermission) -> None:
        """Revoke a specific permission from an agent."""
        if agent_id in self._granted_permissions:
            self._granted_permissions[agent_id].discard(str(permission))
            logger.info("permission_revoked", agent=agent_id, permission=str(permission))

    def validate_permissions(
        self, agent_id: str, required_permissions: List[CapabilityPermission]
    ) -> None:
        """
        Validate that the agent has all required permissions.
        Raises PermissionDeniedError if any are missing.
        """
        if not required_permissions:
            return

        granted = self._granted_permissions.get(agent_id, set())
        for req in required_permissions:
            if str(req) not in granted:
                logger.error("permission_denied", agent=agent_id, missing=str(req))
                raise PermissionDeniedError(f"Agent {agent_id} lacks permission: {req}")

        logger.debug(
            "permissions_validated", agent=agent_id, required=[str(p) for p in required_permissions]
        )
