import json, pytest
from app.agent.runner import run_with_tools

class FakeMcp:
    async def list_openai_tools(self):
        return [{"type":"function","function":{"name":"lastminute__search_flights"}},
                {"type":"function","function":{"name":"lastminute__search_only_hotel"}}]
    async def call_tool(self, name, args):
        return json.dumps([{"price": 100, "tool": name, "args": args}])

class FakeLLM:
    """Prima risposta chiama un tool, seconda risponde testo."""
    def __init__(self): self.calls = 0
    async def complete(self, messages, tools):
        self.calls += 1
        if self.calls == 1:
            return type("M", (), {"content": None, "tool_calls": [
                type("T", (), {"id": "t1", "function": type("F", (), {
                    "name": "lastminute__search_flights",
                    "arguments": json.dumps({"departure":"MXP","arrival":"TFS","start_date":"2026-08-19"})})()})()]})()
        return type("M", (), {"content": "Trovato 1 volo.", "tool_calls": None})()

@pytest.mark.asyncio
async def test_runner_executes_only_perimeter_tool():
    llm, mcp = FakeLLM(), FakeMcp()
    out = await run_with_tools(llm, mcp, "flight", "sys", [{"role":"user","content":"voli"}])
    assert out["content"] == "Trovato 1 volo."
    assert len(out["calls"]) == 1
    assert out["calls"][0]["name"] == "lastminute__search_flights"

@pytest.mark.asyncio
async def test_runner_passes_only_filtered_tools_to_llm():
    seen = {}
    class SpyLLM(FakeLLM):
        async def complete(self, messages, tools):
            seen["tools"] = [t["function"]["name"] for t in tools]
            return type("M", (), {"content": "ok", "tool_calls": None})()
    await run_with_tools(SpyLLM(), FakeMcp(), "flight", "sys", [{"role":"user","content":"x"}])
    assert "lastminute__search_only_hotel" not in seen["tools"]
    assert "lastminute__search_flights" in seen["tools"]
