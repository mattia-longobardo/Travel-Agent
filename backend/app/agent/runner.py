import json
from app.agent.tool_perimeters import filter_tools

async def run_with_tools(llm, mcp, agent, system, user_messages, max_iters=4):
    all_tools = await mcp.list_openai_tools()
    tools = filter_tools(all_tools, agent)
    messages = [{"role": "system", "content": system}] + list(user_messages)
    executed = []
    for _ in range(max_iters):
        msg = await llm.complete(messages, tools)
        tcs = getattr(msg, "tool_calls", None)
        if not tcs:
            return {"content": msg.content or "", "calls": executed}
        messages.append({"role": "assistant", "content": msg.content,
                         "tool_calls": [{"id": tc.id, "type": "function",
                             "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                             for tc in tcs]})
        for tc in tcs:
            args = json.loads(tc.function.arguments or "{}")
            result = await mcp.call_tool(tc.function.name, args)
            executed.append({"name": tc.function.name, "arguments": args, "result": result})
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})
    return {"content": "", "calls": executed}
