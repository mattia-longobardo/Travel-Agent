import json, pytest
from app.agent.llm import OpenAILLM
from app.agent import telemetry

class FakeChat:
    def __init__(self, content, usage=None): self._content = content; self._usage = usage
    async def create(self, **kw):
        return type("R", (), {
            "choices": [type("C", (), {
                "message": type("M", (), {"content": self._content, "tool_calls": None})()})()],
            "usage": self._usage})()

class FakeClient:
    def __init__(self, content, usage=None):
        self.chat = type("X", (), {"completions": FakeChat(content, usage)})()

@pytest.mark.asyncio
async def test_complete_json_parses_object():
    llm = OpenAILLM(FakeClient('{"adults": 2}'), "gpt-5.4")
    out = await llm.complete_json("sys", "user")
    assert out["adults"] == 2

@pytest.mark.asyncio
async def test_complete_text_returns_string():
    llm = OpenAILLM(FakeClient("ciao"), "gpt-5.4")
    assert await llm.complete_text("s", "u") == "ciao"


@pytest.mark.asyncio
async def test_records_usage_into_telemetry():
    usage = type("U", (), {"prompt_tokens": 10, "completion_tokens": 4})()
    llm = OpenAILLM(FakeClient("ciao", usage), "gpt-5.4")
    tok = telemetry.start_run()
    await llm.complete_text("s", "u")
    assert telemetry.snapshot()["total_tokens"] == 14
    telemetry.reset(tok)
