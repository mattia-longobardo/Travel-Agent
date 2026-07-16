from contextlib import asynccontextmanager


@asynccontextmanager
async def _default_factory(spec: dict):
    transport = spec.get("transport", "http")
    if transport == "stdio":
        from mcp import StdioServerParameters
        from mcp.client.stdio import stdio_client
        from mcp import ClientSession
        params = StdioServerParameters(command=spec["command"], args=spec["args"])
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                yield session
    else:
        from mcp.client.streamable_http import streamablehttp_client
        from mcp import ClientSession
        async with streamablehttp_client(spec["url"]) as (read, write, _):
            async with ClientSession(read, write) as session:
                yield session


class McpManager:
    def __init__(self, servers: dict[str, dict], session_factory=_default_factory):
        self.servers = servers
        self._factory = session_factory
        self._index: dict[str, tuple[str, str]] = {}  # namespaced -> (server, tool)
        self._tools_cache: list[dict] | None = None

    async def list_openai_tools(self) -> list[dict]:
        # The remote tool catalogue is static for the life of the process; cache it so
        # we don't re-open a session (re-spawning 'npx mcp-remote') on every agent node.
        if self._tools_cache is not None:
            return self._tools_cache
        tools = []
        self._index.clear()
        for server, spec in self.servers.items():
            async with self._factory(spec) as session:
                await session.initialize()
                res = await session.list_tools()
                for t in res.tools:
                    ns = f"{server}__{t.name}"
                    self._index[ns] = (server, t.name)
                    tools.append({
                        "type": "function",
                        "function": {
                            "name": ns,
                            "description": t.description or "",
                            "parameters": t.inputSchema or {"type": "object", "properties": {}},
                        },
                    })
        self._tools_cache = tools
        return tools

    async def call_tool(self, name: str, arguments: dict) -> str:
        if name not in self._index:
            # discovery may not have run in this process; refresh
            await self.list_openai_tools()
        if name not in self._index:
            return f"[unknown tool: {name}]"
        server, tool = self._index[name]
        spec = self.servers[server]
        async with self._factory(spec) as session:
            await session.initialize()
            res = await session.call_tool(tool, arguments)
            parts = [c.text for c in res.content if getattr(c, "type", None) == "text"]
            return "\n".join(parts) if parts else "[]"
