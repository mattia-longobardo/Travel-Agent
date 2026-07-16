import json

import pytest

from app import property_urls


class MemoryRedis:
    def __init__(self):
        self.values = {}
        self.set_calls = []

    async def get(self, key):
        return self.values.get(key)

    async def set(self, key, value, ex=None):
        self.values[key] = value
        self.set_calls.append((key, value, ex))


def test_safe_public_property_url_requires_exact_storefront_path_and_id():
    expected = (
        "https://www.it.lastminute.com/hotel/portogallo/santa-cruz/"
        "dom-pedro-garajau_hid-20344"
    )
    assert property_urls.safe_public_property_url(expected, hotel_id=20344) == expected
    assert property_urls.safe_public_property_url(expected, hotel_id=7) is None
    assert property_urls.safe_public_property_url(
        "https://www.it.lastminute.com/s/tsx/20344?pageType=review", hotel_id=20344,
    ) is None
    assert property_urls.safe_public_property_url(
        "https://evil.example/hotel/portogallo/santa-cruz/x_hid-20344", hotel_id=20344,
    ) is None
    assert property_urls.safe_public_property_url(
        "https://www.it.lastminute.com:not-a-port/hotel/x/x/x_hid-20344", hotel_id=20344,
    ) is None


def test_extract_canonical_url_matches_the_exact_hotel_id():
    document = """
    [Other](https://www.it.lastminute.com/hotel/italia/roma/other_hid-7)
    [Dom Pedro](https://www.it.lastminute.com/hotel/portogallo/santa-cruz/dom-pedro-garajau_hid-20344)
    """
    assert property_urls._extract_canonical_url(document, 20344) == (
        "https://www.it.lastminute.com/hotel/portogallo/santa-cruz/"
        "dom-pedro-garajau_hid-20344"
    )


@pytest.mark.asyncio
async def test_resolver_recovers_and_caches_canonical_public_page(monkeypatch):
    redis = MemoryRedis()
    seen = []

    class Response:
        payload = {"data": {
            "httpStatus": 200,
            "metadata": {"og:url": (
                "https://www.it.lastminute.com/hotel/portogallo/santa-cruz/"
                "dom-pedro-garajau_hid-20344"
            )},
            "content": "",
        }}
        content = json.dumps(payload).encode()
        text = content.decode()

        def raise_for_status(self):
            return None

        def json(self):
            return self.payload

    class Client:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def get(self, url):
            seen.append(url)
            return Response()

    monkeypatch.setattr(property_urls, "get_redis", lambda: redis)
    monkeypatch.setattr(property_urls.httpx, "AsyncClient", Client)

    expected = (
        "https://www.it.lastminute.com/hotel/portogallo/santa-cruz/"
        "dom-pedro-garajau_hid-20344"
    )
    assert await property_urls.resolve_public_property_url(20344) == expected
    assert await property_urls.resolve_public_property_url(20344) == expected
    assert seen == [
        "https://r.jina.ai/http://www.it.lastminute.com/hotel/x/x/property_hid-20344"
    ]
    assert redis.set_calls == [(
        "property-public-url:v2:20344", expected, property_urls._CANONICAL_TTL_SECONDS,
    )]


@pytest.mark.asyncio
async def test_resolver_hides_cta_and_negative_caches_when_public_page_is_404(monkeypatch):
    redis = MemoryRedis()
    seen = []

    class Response:
        payload = {"data": {
            "httpStatus": 404,
            "metadata": {"og:url": "https://www.it.lastminute.com/errors/error"},
            "content": "Pagina non disponibile",
        }}
        content = json.dumps(payload).encode()
        text = content.decode()

        def raise_for_status(self):
            return None

        def json(self):
            return self.payload

    class Client:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def get(self, url):
            seen.append(url)
            return Response()

    monkeypatch.setattr(property_urls, "get_redis", lambda: redis)
    monkeypatch.setattr(property_urls.httpx, "AsyncClient", Client)

    assert await property_urls.resolve_public_property_url(12978711) is None
    assert await property_urls.resolve_public_property_url(12978711) is None
    assert seen == [
        "https://r.jina.ai/http://www.it.lastminute.com/hotel/x/x/property_hid-12978711"
    ]
    assert redis.set_calls == [(
        "property-public-url:v2:12978711", "null", property_urls._NEGATIVE_TTL_SECONDS,
    )]
