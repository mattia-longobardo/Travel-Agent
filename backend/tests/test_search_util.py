import asyncio
import pytest
from app.agent.search import bounded_call


class SlowMcp:
    async def call_tool(self, name, args):
        await asyncio.sleep(5)
        return "[1]"


class OkMcp:
    def __init__(self): self.active = 0; self.peak = 0
    async def call_tool(self, name, args):
        self.active += 1
        self.peak = max(self.peak, self.active)
        await asyncio.sleep(0.01)
        self.active -= 1
        return '[{"x": 1}]'


class BoomMcp:
    async def call_tool(self, name, args):
        raise RuntimeError("boom")


@pytest.mark.asyncio
async def test_bounded_call_times_out_to_empty_result():
    sem = asyncio.Semaphore(4)
    assert await bounded_call(SlowMcp(), "t", {}, sem, timeout=0.05) == "[]"


@pytest.mark.asyncio
async def test_bounded_call_swallows_errors():
    sem = asyncio.Semaphore(4)
    assert await bounded_call(BoomMcp(), "t", {}, sem) == "[]"


@pytest.mark.asyncio
async def test_bounded_call_limits_concurrency():
    mcp = OkMcp()
    sem = asyncio.Semaphore(2)
    await asyncio.gather(*(bounded_call(mcp, "t", {}, sem) for _ in range(8)))
    assert mcp.peak <= 2
