import datetime
from typing import Dict, List, Optional
from core.models.tool import ResourceLease
from core.logging.logger import logger
from core.utils.helpers import generate_uuid

class ResourceConflictError(Exception):
    """Raised when a resource cannot be leased due to conflicts."""
    pass


class ResourceManager:
    """
    Manages abstract resources using leases.
    Tracks ownership, grants/releases leases, prevents conflicts.
    """

    def __init__(self) -> None:
        # map: resource_name -> current active lease
        self._active_leases: Dict[str, ResourceLease] = {}

    def acquire_lease(self, resource_name: str, owner_id: str, duration_sec: Optional[int] = None) -> ResourceLease:
        """
        Attempt to acquire a lease for a resource.
        """
        # Clean up expired leases first
        self._cleanup_expired()

        if resource_name in self._active_leases:
            current_lease = self._active_leases[resource_name]
            logger.warning(
                "resource_conflict",
                resource=resource_name,
                requested_by=owner_id,
                owned_by=current_lease.owner_id
            )
            raise ResourceConflictError(f"Resource '{resource_name}' is currently leased by {current_lease.owner_id}.")

        now = datetime.datetime.utcnow()
        expires_at = now + datetime.timedelta(seconds=duration_sec) if duration_sec else None

        lease = ResourceLease(
            lease_id=generate_uuid(),
            resource_name=resource_name,
            granted_at=now,
            expires_at=expires_at,
            owner_id=owner_id
        )
        self._active_leases[resource_name] = lease

        logger.info("lease_acquired", resource=resource_name, owner=owner_id, lease_id=lease.lease_id)
        return lease

    def release_lease(self, lease: ResourceLease) -> None:
        """Release a previously acquired lease."""
        if lease.resource_name in self._active_leases:
            current_lease = self._active_leases[lease.resource_name]
            if current_lease.lease_id == lease.lease_id:
                del self._active_leases[lease.resource_name]
                logger.info("lease_released", resource=lease.resource_name, lease_id=lease.lease_id)
            else:
                logger.warning("lease_release_mismatch", resource=lease.resource_name, attempted=lease.lease_id)

    def _cleanup_expired(self) -> None:
        """Remove leases that have expired."""
        now = datetime.datetime.utcnow()
        expired = []
        for res_name, lease in self._active_leases.items():
            if lease.expires_at and lease.expires_at < now:
                expired.append(res_name)
        
        for res_name in expired:
            logger.info("lease_expired", resource=res_name, lease_id=self._active_leases[res_name].lease_id)
            del self._active_leases[res_name]

    def get_active_leases(self) -> List[ResourceLease]:
        """Return all currently active and non-expired leases."""
        self._cleanup_expired()
        return list(self._active_leases.values())
