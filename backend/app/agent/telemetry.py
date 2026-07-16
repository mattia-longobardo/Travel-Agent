import contextvars

_acc: contextvars.ContextVar[dict | None] = contextvars.ContextVar("telemetry_acc", default=None)


def start_run():
    return _acc.set({"prompt_tokens": 0, "completion_tokens": 0})


def add_usage(prompt: int, completion: int) -> None:
    acc = _acc.get()
    if acc is not None:
        acc["prompt_tokens"] += int(prompt or 0)
        acc["completion_tokens"] += int(completion or 0)


def snapshot() -> dict:
    acc = _acc.get() or {"prompt_tokens": 0, "completion_tokens": 0}
    return {"prompt_tokens": acc["prompt_tokens"], "completion_tokens": acc["completion_tokens"],
            "total_tokens": acc["prompt_tokens"] + acc["completion_tokens"]}


def reset(token) -> None:
    try:
        _acc.reset(token)
    except Exception:
        pass
