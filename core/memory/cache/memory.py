"""Key-value memory cache skeleton implementation."""

from typing import Any, Dict, Optional


class MemoryCache:
    """In-memory key-value cache skeleton."""

    def __init__(self) -> None:
        self._cache: Dict[str, Any] = {}

    async def get(self, key: str) -> Optional[Any]:
        return self._cache.get(key)

    async def set(self, key: str, value: Any) -> None:
        self._cache[key] = value

    async def delete(self, key: str) -> None:
        self._cache.pop(key, None)
