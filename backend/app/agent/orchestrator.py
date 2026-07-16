import json


async def run_agent(openai_client, model, system_prompt, history, mcp, max_iters=5):
    tools = await mcp.list_openai_tools()
    messages = [{"role": "system", "content": system_prompt}] + history
    executed = []
    for _ in range(max_iters):
        resp = await openai_client.chat.completions.create(
            model=model, messages=messages, tools=tools, tool_choice="auto")
        msg = resp.choices[0].message
        if not getattr(msg, "tool_calls", None):
            return {"content": msg.content or "", "tool_calls": executed}
        messages.append({"role": "assistant", "content": msg.content,
                         "tool_calls": [{"id": tc.id, "type": "function",
                                         "function": {"name": tc.function.name,
                                                      "arguments": tc.function.arguments}}
                                        for tc in msg.tool_calls]})
        for tc in msg.tool_calls:
            args = json.loads(tc.function.arguments or "{}")
            result = await mcp.call_tool(tc.function.name, args)
            executed.append({"name": tc.function.name, "arguments": args, "result": result})
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})
    return {"content": "Non sono riuscito a completare la ricerca entro il limite di passi.",
            "tool_calls": executed}
