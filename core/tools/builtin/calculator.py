from typing import Any
from core.tools.base import BaseTool
from core.models.tool import ToolManifest, ToolCategory, ToolExecutionContext
from core.models.capability import CapabilityVersion


class CalculatorTool(BaseTool):
    """A mock tool that performs basic arithmetic."""

    def get_manifest(self) -> ToolManifest:
        return ToolManifest(
            name="calculator_tool",
            version=CapabilityVersion(major=1, minor=1, patch=0),
            description="Performs simple math operations.",
            capabilities=["math.add", "math.subtract"],
            category=ToolCategory.MOCK,
            entry_point="core.tools.builtin.calculator.CalculatorTool"
        )

    async def execute(self, context: ToolExecutionContext, **kwargs: Any) -> Any:
        a = kwargs.get("a", 0)
        b = kwargs.get("b", 0)
        operation = context.request.capability_name
        
        if operation == "math.add":
            return a + b
        elif operation == "math.subtract":
            return a - b
        else:
            raise ValueError(f"Unsupported capability: {operation}")
