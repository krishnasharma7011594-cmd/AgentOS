from typing import Any

from core.models.capability import CapabilityPermission, CapabilityVersion
from core.models.tool import ToolCategory, ToolExecutionContext, ToolManifest
from core.tools.base import BaseTool


class FileMetadataTool(BaseTool):
    """A mock tool that retrieves file metadata, demonstrating permissions and resources."""

    def get_manifest(self) -> ToolManifest:
        return ToolManifest(
            name="file_metadata_tool",
            version=CapabilityVersion(major=1, minor=0, patch=0),
            description="Retrieves basic file metadata.",
            capabilities=["filesystem.metadata"],
            permissions=[CapabilityPermission(resource="filesystem", action="read")],
            required_resources=["filesystem_access"],
            category=ToolCategory.FILESYSTEM,
            entry_point="core.tools.builtin.file_metadata.FileMetadataTool",
        )

    async def execute(self, context: ToolExecutionContext, **kwargs: Any) -> Any:
        # Simulate accessing the file system
        path = kwargs.get("path", ".")

        # Since this is a mock tool, we don't actually do deep os.stat for safety
        # in some environments, but we can return dummy metadata for testing.
        return {"path": path, "type": "file", "size": 1024, "permissions": "rwxr-xr-x"}
