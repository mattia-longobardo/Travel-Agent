import pytest
from contextlib import asynccontextmanager
from app.agent.mcp_manager import McpManager


class FakeTool:
    def __init__(self, name):
        self.name = name
        self.description = "d"
        self.inputSchema = {"type": "object", "properties": {}}


class FakeSession:
    async def initialize(self):
        pass

    async def list_tools(self):
        class R:
            tools = [FakeTool("search_flights")]
        return R()

    async def call_tool(self, name, arguments):
        class C:
            content = [type("T", (), {"type": "text", "text": '[{"type":"flight","price":10}]'})()]
        return C()


@asynccontextmanager
async def fake_factory(spec):
    yield FakeSession()


@pytest.mark.asyncio
async def test_list_and_call_stdio_spec():
    """list_openai_tools and call_tool work with a stdio spec dict."""
    servers = {
        "lastminute": {
            "transport": "stdio",
            "command": "npx",
            "args": ["-y", "mcp-remote", "https://mcp.lastminute.com/mcp"],
        }
    }
    m = McpManager(servers, session_factory=fake_factory)
    tools = await m.list_openai_tools()
    assert tools[0]["function"]["name"] == "lastminute__search_flights"
    out = await m.call_tool("lastminute__search_flights", {"origin": "MXP"})
    assert "flight" in out


@pytest.mark.asyncio
async def test_list_openai_tools_is_cached():
    """The tool list is fetched once and cached: repeated calls must not re-open
    a session (which, for stdio, would re-spawn 'npx mcp-remote' — the latency bug)."""
    calls = {"n": 0}

    @asynccontextmanager
    async def counting_factory(spec):
        calls["n"] += 1
        yield FakeSession()

    servers = {"lastminute": {"transport": "stdio", "command": "npx",
                              "args": ["-y", "mcp-remote", "https://x"]}}
    m = McpManager(servers, session_factory=counting_factory)
    await m.list_openai_tools()
    await m.list_openai_tools()
    await m.list_openai_tools()
    assert calls["n"] == 1, "tool list must be fetched only once (cached)"


@pytest.mark.asyncio
async def test_call_tool_unknown_returns_error_string():
    """call_tool on an unknown name returns a string containing 'unknown tool'."""
    servers = {
        "lastminute": {
            "transport": "stdio",
            "command": "npx",
            "args": ["-y", "mcp-remote", "https://mcp.lastminute.com/mcp"],
        }
    }
    m = McpManager(servers, session_factory=fake_factory)
    # Intentionally do NOT call list_openai_tools first — McpManager must refresh
    # and still return the error string for a name that doesn't exist anywhere.
    result = await m.call_tool("nonexistent__tool", {"x": 1})
    assert "unknown tool" in result
