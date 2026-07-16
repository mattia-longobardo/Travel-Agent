import json


def _record_usage(resp):
    u = getattr(resp, "usage", None)
    if u is not None:
        from app.agent import telemetry
        telemetry.add_usage(getattr(u, "prompt_tokens", 0), getattr(u, "completion_tokens", 0))


class OpenAILLM:
    def __init__(self, client, model):
        self.client = client
        self.model = model

    async def complete(self, messages, tools):
        kw = {"model": self.model, "messages": messages}
        if tools:
            kw["tools"] = tools
            kw["tool_choice"] = "auto"
        resp = await self.client.chat.completions.create(**kw)
        _record_usage(resp)
        return resp.choices[0].message

    async def complete_json(self, system, user) -> dict:
        resp = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            response_format={"type": "json_object"})
        _record_usage(resp)
        try:
            return json.loads(resp.choices[0].message.content or "{}")
        except Exception:
            return {}

    async def complete_text(self, system, user) -> str:
        resp = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}])
        _record_usage(resp)
        return resp.choices[0].message.content or ""
