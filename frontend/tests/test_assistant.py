"""Tests for the AI assistant service layer."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from frontend.services.assistant.context import build_project_context
from frontend.services.assistant.prompt import build_system_prompt
from frontend.services.assistant.session import ChatSession, SessionManager
from frontend.services.assistant.tools.base import ToolContext, ToolDef, ToolRegistry, ToolResult


class TestToolResult:
    def test_success_result(self):
        r = ToolResult("ok")
        assert r.output == "ok"
        assert r.is_error is False

    def test_error_result(self):
        r = ToolResult("failed", is_error=True)
        assert r.output == "failed"
        assert r.is_error is True

    def test_to_api_format(self):
        r = ToolResult("output text")
        fmt = r.to_api_format()
        assert fmt["type"] == "tool_result"
        assert fmt["content"] == "output text"
        assert "is_error" not in fmt

    def test_error_to_api_format(self):
        r = ToolResult("bad", is_error=True)
        fmt = r.to_api_format()
        assert fmt["is_error"] is True


class TestToolRegistry:
    def setup_method(self):
        self.registry = ToolRegistry()

    def test_register_and_get(self):
        def handler(ctx, args):
            return ToolResult("done")

        tool = ToolDef(
            name="test_tool",
            description="A test tool",
            parameters={"type": "object", "properties": {}},
            handler=handler,
            category="test",
        )
        self.registry.register(tool)
        assert self.registry.get("test_tool") is tool

    def test_get_nonexistent(self):
        assert self.registry.get("nonexistent") is None

    def test_list_tools(self):
        for i in range(3):
            tool = ToolDef(
                name=f"tool_{i}",
                description=f"Tool {i}",
                parameters={"type": "object", "properties": {}},
                handler=lambda ctx, args: ToolResult("ok"),
                category="test",
            )
            self.registry.register(tool)
        tools = self.registry.list_tools()
        assert len(tools) == 3

    def test_to_api_format(self):
        tool = ToolDef(
            name="api_tool",
            description="For API",
            parameters={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "The name"},
                },
                "required": ["name"],
            },
            handler=lambda ctx, args: ToolResult("ok"),
            category="test",
        )
        self.registry.register(tool)
        api_tools = self.registry.to_api_format()
        assert len(api_tools) == 1
        assert api_tools[0]["name"] == "api_tool"
        assert api_tools[0]["description"] == "For API"
        assert api_tools[0]["input_schema"]["properties"]["name"]["type"] == "string"

    def test_execute_success(self):
        def handler(ctx, args):
            return ToolResult(f"got: {args.get('value', '')}")

        tool = ToolDef(
            name="exec_tool",
            description="Exec",
            parameters={"type": "object", "properties": {"value": {"type": "string"}}},
            handler=handler,
            category="test",
        )
        self.registry.register(tool)
        ctx = ToolContext(
            store=MagicMock(),
            task_runner=MagicMock(),
            server_manager=MagicMock(),
            project_root="/tmp",
        )
        result = self.registry.execute("exec_tool", {"value": "hello"}, ctx)
        assert result.output == "got: hello"
        assert result.is_error is False

    def test_execute_nonexistent_tool(self):
        ctx = ToolContext(
            store=MagicMock(),
            task_runner=MagicMock(),
            server_manager=MagicMock(),
            project_root="/tmp",
        )
        result = self.registry.execute("missing", {}, ctx)
        assert result.is_error is True
        assert "unknown" in result.output.lower()

    def test_execute_handler_error(self):
        def bad_handler(ctx, args):
            raise ValueError("boom")

        tool = ToolDef(
            name="bad_tool",
            description="Bad",
            parameters={"type": "object", "properties": {}},
            handler=bad_handler,
            category="test",
        )
        self.registry.register(tool)
        ctx = ToolContext(
            store=MagicMock(),
            task_runner=MagicMock(),
            server_manager=MagicMock(),
            project_root="/tmp",
        )
        result = self.registry.execute("bad_tool", {}, ctx)
        assert result.is_error is True
        assert "boom" in result.output


class TestChatSession:
    def test_new_session_empty(self):
        session = ChatSession()
        assert len(session.messages) == 0

    def test_add_user_message(self):
        session = ChatSession()
        session.add_user_message("Hello")
        assert len(session.messages) == 1
        assert session.messages[0]["role"] == "user"
        assert session.messages[0]["content"] == "Hello"

    def test_add_assistant_message(self):
        session = ChatSession()
        session.add_assistant_message("Hi there")
        assert len(session.messages) == 1
        assert session.messages[0]["role"] == "assistant"

    def test_get_api_messages(self):
        session = ChatSession()
        session.add_user_message("Hello")
        session.add_assistant_message("Hi")
        msgs = session.get_api_messages()
        assert len(msgs) == 2
        assert msgs[0]["role"] == "user"
        assert msgs[1]["role"] == "assistant"

    def test_conversation_flow(self):
        session = ChatSession()
        session.add_user_message("Help me train")
        session.add_assistant_message("Sure, let me check your project.")
        session.add_user_message("Use default settings")
        msgs = session.get_api_messages()
        assert len(msgs) == 3
        assert msgs[0]["role"] == "user"
        assert msgs[1]["role"] == "assistant"
        assert msgs[2]["role"] == "user"


class TestSessionManager:
    def test_create_and_get_session(self):
        mgr = SessionManager()
        s1 = mgr.get_or_create("session-1")
        assert isinstance(s1, ChatSession)
        s2 = mgr.get_or_create("session-1")
        assert s1 is s2  # Same object

    def test_different_sessions(self):
        mgr = SessionManager()
        s1 = mgr.get_or_create("a")
        s2 = mgr.get_or_create("b")
        s1.add_user_message("hello")
        assert len(s2.messages) == 0


class TestProjectContext:
    def test_empty_project(self):
        store = MagicMock()
        store.get_project.return_value = None
        server_manager = MagicMock()
        ctx = build_project_context(store, server_manager, None)
        assert isinstance(ctx, str)
        assert "no project" in ctx.lower() or len(ctx) > 0

    def test_with_project(self):
        store = MagicMock()
        store.get_project.return_value = {
            "id": "abc123", "name": "TestBot", "embodiment_tag": "gr1",
            "base_model": "nvidia/GR00T-N1.6-3B",
        }
        store.list_datasets.return_value = [
            {"name": "ds1", "path": "/data/ds1", "episode_count": 50},
        ]
        store.list_models.return_value = []
        store.get_active_runs.return_value = []
        store.list_runs.return_value = []
        server_manager = MagicMock()
        server_manager.status.return_value = "stopped"

        ctx = build_project_context(store, server_manager, "abc123")
        assert "TestBot" in ctx
        assert "ds1" in ctx

    def test_with_active_runs(self):
        store = MagicMock()
        store.get_project.return_value = {
            "id": "abc", "name": "Bot", "embodiment_tag": "gr1",
            "base_model": "nvidia/GR00T-N1.6-3B",
        }
        store.list_datasets.return_value = []
        store.list_models.return_value = []
        store.get_active_runs.return_value = [
            {"id": "run1", "run_type": "training", "status": "running", "project_id": "abc"},
        ]
        store.list_runs.return_value = [
            {"id": "run1", "run_type": "training", "status": "running", "project_id": "abc"},
        ]
        server_manager = MagicMock()
        server_manager.status.return_value = "stopped"

        ctx = build_project_context(store, server_manager, "abc")
        assert "training" in ctx.lower()


class TestSystemPrompt:
    def test_build_with_context(self):
        prompt = build_system_prompt("Current project: TestBot with 5 datasets")
        assert isinstance(prompt, str)
        assert "TestBot" in prompt
        assert len(prompt) > 100

    def test_build_empty_context(self):
        prompt = build_system_prompt("")
        assert isinstance(prompt, str)
        assert len(prompt) > 50


class TestToolRegistrations:
    """Verify that tool modules export valid tool definitions."""

    def _make_registry(self, tool_list):
        registry = ToolRegistry()
        for tool in tool_list:
            registry.register(tool)
        return registry

    def test_workspace_tools(self):
        from frontend.services.assistant.tools.workspace_tools import WORKSPACE_TOOLS
        registry = self._make_registry(WORKSPACE_TOOLS)
        tools = registry.list_tools()
        assert len(tools) >= 4
        names = {t.name for t in tools}
        assert "list_projects" in names
        assert "create_project" in names

    def test_system_tools(self):
        from frontend.services.assistant.tools.system_tools import SYSTEM_TOOLS
        registry = self._make_registry(SYSTEM_TOOLS)
        tools = registry.list_tools()
        assert len(tools) >= 3
        names = {t.name for t in tools}
        assert "get_gpu_status" in names

    def test_data_tools(self):
        from frontend.services.assistant.tools.data_tools import DATA_TOOLS
        registry = self._make_registry(DATA_TOOLS)
        assert len(registry.list_tools()) >= 3

    def test_train_tools(self):
        from frontend.services.assistant.tools.train_tools import TRAIN_TOOLS
        registry = self._make_registry(TRAIN_TOOLS)
        assert len(registry.list_tools()) >= 3

    def test_eval_tools(self):
        from frontend.services.assistant.tools.eval_tools import EVAL_TOOLS
        registry = self._make_registry(EVAL_TOOLS)
        assert len(registry.list_tools()) >= 3

    def test_deploy_tools(self):
        from frontend.services.assistant.tools.deploy_tools import DEPLOY_TOOLS
        registry = self._make_registry(DEPLOY_TOOLS)
        assert len(registry.list_tools()) >= 3

    def test_all_tools_have_valid_api_format(self):
        from frontend.services.assistant.tools.data_tools import DATA_TOOLS
        from frontend.services.assistant.tools.deploy_tools import DEPLOY_TOOLS
        from frontend.services.assistant.tools.eval_tools import EVAL_TOOLS
        from frontend.services.assistant.tools.system_tools import SYSTEM_TOOLS
        from frontend.services.assistant.tools.train_tools import TRAIN_TOOLS
        from frontend.services.assistant.tools.workspace_tools import WORKSPACE_TOOLS

        registry = ToolRegistry()
        for tool_list in [WORKSPACE_TOOLS, SYSTEM_TOOLS, DATA_TOOLS, TRAIN_TOOLS, EVAL_TOOLS, DEPLOY_TOOLS]:
            for tool in tool_list:
                registry.register(tool)

        api_tools = registry.to_api_format()
        assert len(api_tools) >= 20

        for tool in api_tools:
            assert "name" in tool
            assert "description" in tool
            assert "input_schema" in tool
            assert isinstance(tool["name"], str)
            assert isinstance(tool["description"], str)
            assert isinstance(tool["input_schema"], dict)
            assert "type" in tool["input_schema"]
            assert tool["input_schema"]["type"] == "object"

    def test_all_tools_are_tooldef_instances(self):
        from frontend.services.assistant.tools.data_tools import DATA_TOOLS
        from frontend.services.assistant.tools.deploy_tools import DEPLOY_TOOLS
        from frontend.services.assistant.tools.eval_tools import EVAL_TOOLS
        from frontend.services.assistant.tools.system_tools import SYSTEM_TOOLS
        from frontend.services.assistant.tools.train_tools import TRAIN_TOOLS
        from frontend.services.assistant.tools.workspace_tools import WORKSPACE_TOOLS

        all_tools = WORKSPACE_TOOLS + SYSTEM_TOOLS + DATA_TOOLS + TRAIN_TOOLS + EVAL_TOOLS + DEPLOY_TOOLS
        for tool in all_tools:
            assert isinstance(tool, ToolDef), f"{tool} is not a ToolDef"
            assert tool.name, "Tool name must not be empty"
            assert tool.description, f"Tool {tool.name} has no description"
            assert callable(tool.handler), f"Tool {tool.name} handler is not callable"


class TestAgentImport:
    def test_agent_class_importable(self):
        from frontend.services.assistant.agent import WybeAgent
        assert WybeAgent is not None

    def test_agent_greeting_exists(self):
        from frontend.services.assistant.agent import GREETING
        assert isinstance(GREETING, str)
        assert len(GREETING) > 10

    def test_agent_init(self):
        """Agent should initialize even without an API key (graceful degradation)."""
        from frontend.services.assistant.agent import WybeAgent
        agent = WybeAgent(
            store=MagicMock(),
            task_runner=MagicMock(),
            server_manager=MagicMock(),
            project_root="/tmp",
        )
        assert agent is not None
        assert agent.tools is not None
        assert len(agent.tools.list_tools()) >= 20

    def test_agent_registers_all_tools(self):
        from frontend.services.assistant.agent import WybeAgent
        agent = WybeAgent(
            store=MagicMock(),
            task_runner=MagicMock(),
            server_manager=MagicMock(),
            project_root="/tmp",
        )
        tool_names = {t.name for t in agent.tools.list_tools()}
        # Spot-check a tool from each category
        assert "list_projects" in tool_names
        assert "get_gpu_status" in tool_names
        assert "launch_training" in tool_names
        assert "run_open_loop_eval" in tool_names
        assert "deploy_server" in tool_names
