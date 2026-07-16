import pytest

from app.chat_titles import DEFAULT_CHAT_TITLE, clean_chat_title, fallback_chat_title, generate_chat_title


class _FakeCompletions:
    def __init__(self, content):
        self.content = content

    async def create(self, **_kwargs):
        message = type("Message", (), {"content": self.content})()
        choice = type("Choice", (), {"message": message})()
        return type("Response", (), {"choices": [choice]})()


class _FakeClient:
    def __init__(self, content):
        self.chat = type("Chat", (), {"completions": _FakeCompletions(content)})()


def test_clean_chat_title_trims_quotes_punctuation_and_length():
    title = clean_chat_title('  "Weekend romantico a Lisbona con budget medio e hotel centrale."  ')

    assert title == "Weekend romantico a Lisbona con budget medio e hotel"
    assert len(title) <= 60


def test_fallback_chat_title_uses_short_first_message_summary():
    assert fallback_chat_title("Vorrei andare alle Canarie ad agosto con partenza da Milano") == (
        "Vorrei andare alle Canarie ad agosto con"
    )
    assert fallback_chat_title("   ") == DEFAULT_CHAT_TITLE


@pytest.mark.asyncio
async def test_generate_chat_title_uses_model_json_response():
    title = await generate_chat_title(
        "Vorrei una settimana alle Canarie ad agosto",
        _FakeClient('{"title":"Canarie ad agosto"}'),
        "gpt-test",
    )

    assert title == "Canarie ad agosto"


@pytest.mark.asyncio
async def test_generate_chat_title_falls_back_on_model_error():
    class BrokenCompletions:
        async def create(self, **_kwargs):
            raise RuntimeError("boom")

    client = type("Client", (), {
        "chat": type("Chat", (), {"completions": BrokenCompletions()})()
    })()

    assert await generate_chat_title("Canarie agosto partenza Milano", client, "gpt-test") == (
        "Canarie agosto partenza Milano"
    )
