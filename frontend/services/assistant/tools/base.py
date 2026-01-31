"""Base tool infrastructure for the Wybe assistant."""

from __future__ import annotations

import json
import logging
import traceback
from dataclasses import dataclass, field
from typing import Any, Callable

logger = logging.getLogger(__name__)


@dataclass
class ToolResult:
    """Result from executing a tool."""

    output: str
    is_error: bool = False

    def to_api_format(self) -> dict:
        result: dict[str, Any] = {"type": "tool_result", "content": self.output}
        if self.is_error:
            result["is_error"] = True
        return result


@dataclass
class ToolContext:
    """Shared context available to all tool functions."""

    store: Any  # WorkspaceStore
    task_runner: Any  # TaskRunner
    server_manager: Any  # ServerManager
    project_root: str = ""
    current_project_id: str | None = None


@dataclass
class ToolDef:
    """Definition of a single tool."""

    name: str
    description: str
    parameters: dict  # JSON Schema for input_schema
    handler: Callable[[ToolContext, dict], ToolResult]
    category: str = ""


class ToolRegistry:
    """Registry of all available tools."""

    def __init__(self):
        self._tools: dict[str, ToolDef] = {}

    def register(self, tool: ToolDef) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> ToolDef | None:
        return self._tools.get(name)

    def list_tools(self) -> list[ToolDef]:
        return list(self._tools.values())

    def to_api_format(self) -> list[dict]:
        """Convert all tools to Anthropic API format."""
        result = []
        for tool in self._tools.values():
            result.append({
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.parameters,
            })
        return result

    def execute(self, name: str, args: dict, context: ToolContext) -> ToolResult:
        """Execute a tool by name with the given arguments."""
        tool = self._tools.get(name)
        if tool is None:
            return ToolResult(output=f"Unknown tool: {name}", is_error=True)

        try:
            return tool.handler(context, args)
        except Exception as exc:
            logger.exception("Tool %s failed", name)
            return ToolResult(
                output=f"Tool execution failed: {exc}\n{traceback.format_exc()}",
                is_error=True,
            )


def json_output(data: Any) -> str:
    """Format data as a readable JSON string for tool output."""
    if isinstance(data, str):
        return data
    return json.dumps(data, indent=2, default=str)
