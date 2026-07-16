import json
import pytest
from app.agent.orchestrator import run_agent

class FakeMsg:
    def __init__(self, content=None, tool_calls=None):
        self.content = content; self.tool_calls = tool_calls

class FakeToolCall:
    def __init__(self, id, name, args):
        self.id = id; self.type = "function"
        self.function = type("F", (), {"name": name, "arguments": json.dumps(args)})()

class FakeChoice:
    def __init__(self, msg): self.message = msg

class FakeResp:
    def __init__(self, msg): self.choices = [FakeChoice(msg)]

class FakeCompletions:
    def __init__(self, scripted): self.scripted = scripted; self.calls = 0
    async def create(self, **kw):
        r = self.scripted[self.calls]; self.calls += 1; return r

class FakeOpenAI:
    def __init__(self, scripted):
        self.chat = type("C", (), {"completions": FakeCompletions(scripted)})()

class FakeMcp:
    async def list_openai_tools(self): return [{"type":"function","function":{"name":"lastminute__search_flights","parameters":{}}}]
    async def call_tool(self, name, args): return '[{"type":"flight","price":99}]'

@pytest.mark.asyncio
async def test_runs_tool_then_answers():
    scripted = [
        FakeResp(FakeMsg(tool_calls=[FakeToolCall("c1", "lastminute__search_flights", {"origin":"MXP"})])),
        FakeResp(FakeMsg(content="Ecco 2 opzioni di volo...")),
    ]
    out = await run_agent(FakeOpenAI(scripted), "gpt-4.1", "sys", [{"role":"user","content":"trova voli"}], FakeMcp())
    assert "opzioni" in out["content"]
    assert out["tool_calls"][0]["name"] == "lastminute__search_flights"
