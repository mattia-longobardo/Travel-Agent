"""Bounded, fault-tolerant fan-out for MCP search calls.

Search nodes probe destinations × candidate periods × origins. Sequential calls made a
5-destination flexible-date search take minutes; a naive gather would spawn dozens of
`npx mcp-remote` subprocesses at once. So the fan-out is parallel but bounded, and each
call is individually timed out: a hung or failing call degrades to an empty result and
the rest of the search still completes.
"""
import asyncio

CONCURRENCY = 4
CALL_TIMEOUT = 45.0  # seconds per MCP search call


async def bounded_call(mcp, tool: str, args: dict, sem: asyncio.Semaphore,
                       timeout: float = CALL_TIMEOUT) -> str:
    """One MCP tool call under the shared semaphore with a hard timeout.
    Any failure (error, timeout, cancellation of the MCP layer) returns "[]" so the
    caller's normalizer yields zero offers instead of crashing the node."""
    try:
        async with sem:
            async with asyncio.timeout(timeout):
                return await mcp.call_tool(tool, args)
    except Exception:
        return "[]"
