import importlib
from typing import List

from core.logging.logger import logger
from core.models.capability import CapabilityDescriptor, CapabilityMetadata, CapabilityScope
from core.tools.base import BaseTool
from core.tools.capability_registry import CapabilityRegistry
from core.tools.tool_registry import ToolRegistry


class ToolLoader:
    """
    Responsible for discovering, loading, unloading, and reloading tool implementations.
    Reads ToolManifests and populates the registries.
    """

    def __init__(
        self, tool_registry: ToolRegistry, capability_registry: CapabilityRegistry
    ) -> None:
        self._tool_registry = tool_registry
        self._capability_registry = capability_registry
        self._loaded_modules: List[str] = []

    async def load_tool(self, module_path: str, class_name: str) -> None:
        """
        Dynamically load a tool from a module path and register it.
        Example: module_path="core.tools.builtin.echo", class_name="EchoTool"
        """
        try:
            module = importlib.import_module(module_path)
            tool_class = getattr(module, class_name)
            tool_instance: BaseTool = tool_class()

            # Initialize tool lifecycle
            await tool_instance.initialize()

            # Register tool
            self._tool_registry.register(tool_instance)
            self._loaded_modules.append(module_path)

            # Register its capabilities
            manifest = tool_instance.get_manifest()
            for cap_name in manifest.capabilities:
                # We create a simple CapabilityDescriptor for each exposed capability.
                # In a real system, capability definitions might be loaded separately,
                # but here we infer it from the tool manifest.
                desc = CapabilityDescriptor(
                    metadata=CapabilityMetadata(
                        name=cap_name,
                        version=manifest.version,
                        description=f"Provides {cap_name} functionality.",
                        author=manifest.author,
                    ),
                    scope=CapabilityScope.LOCAL,
                    permissions=manifest.permissions,
                    # For simplicity, passing manifest dependencies to the capability
                )
                self._capability_registry.register(desc)

            logger.info("tool_loaded", module=module_path, class_name=class_name)

        except Exception as e:
            logger.error("tool_load_failed", module=module_path, error=str(e))
            raise

    async def unload_tool(self, name: str) -> None:
        """Unload a tool by name, calling its shutdown hook."""
        tool = self._tool_registry.get(name)
        if tool:
            await tool.shutdown()
            self._tool_registry.unregister(name)

            # Remove capabilities only provided by this tool
            # (Simplified: in a robust system with multiple implementations,
            # we'd check if other tools still provide it).
            for cap in tool.get_manifest().capabilities:
                self._capability_registry.unregister(cap)

    async def reload_tool(self, module_path: str, class_name: str, name: str) -> None:
        """Reload a tool."""
        await self.unload_tool(name)
        # Force reload module
        if module_path in self._loaded_modules:
            import sys

            if module_path in sys.modules:
                importlib.reload(sys.modules[module_path])
        await self.load_tool(module_path, class_name)
