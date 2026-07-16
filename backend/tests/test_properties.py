import json

import pytest

from app.routers import properties
from app.routers.properties import property_details


@pytest.fixture(autouse=True)
def stub_public_property_resolver(monkeypatch):
    async def resolve(hotel_id):
        return f"https://www.it.lastminute.com/hotel/x/x/property_hid-{hotel_id}"

    monkeypatch.setattr(properties, "resolve_public_property_url", resolve)


class FakeMcp:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    async def call_tool(self, name, args):
        self.calls.append((name, args))
        return json.dumps(self.payload)


@pytest.mark.asyncio
async def test_property_details_exposes_characteristics_without_checkout_ids():
    mcp = FakeMcp({
        "success": True,
        "pricing_id": "SECRET-PRICING",
        "hotel": {
            "id": 77,
            "name": "Casa Navona",
            "address": "Roma",
            "description": "Appartamento nel centro storico.",
            "gallery_links": ["[Photo 1](https://cdn.example/one.jpg)"],
        },
        "policies": {"wifi_free": True, "pets_allowed": False},
        "room_options": [{
            "rate_id": "SECRET-RATE", "room_name": "Appartamento",
            "meal_plan": "ROOM_ONLY", "price": 500, "currency": "GBP",
            "cancellation": "Free cancellation",
        }],
    })
    out = await property_details(
        hotel_id=77, search_id=123, date_from="2026-09-01", date_to="2026-09-05",
        user=object(), mcp=mcp,
    )
    assert out["name"] == "Casa Navona"
    assert out["original_url"] == (
        "https://www.it.lastminute.com/hotel/x/x/property_hid-77"
    )
    assert out["gallery"] == ["https://cdn.example/one.jpg"]
    assert out["rooms"] == [{
        "name": "Appartamento", "meal_plan": "ROOM_ONLY",
        "cancellation": "Free cancellation",
        "deposit_required": None,
        "price": 500,
        "currency": "GBP",
        "price_note": None,
    }]
    serialized = json.dumps(out)
    assert "SECRET" not in serialized
    assert mcp.calls[0][1]["hotel_internal_id"] == 77
    assert out["details_status"] == "complete"
    assert out["partial"] is False


@pytest.mark.asyncio
async def test_property_details_returns_partial_payload_when_provider_fails():
    class FailingMcp:
        async def call_tool(self, name, args):
            raise RuntimeError("provider unavailable")

    out = await property_details(
        hotel_id=20344,
        search_id=123,
        date_from="2026-09-09",
        date_to="2026-09-15",
        user=object(),
        mcp=FailingMcp(),
    )

    assert out == {
        "id": 20344,
        "name": None,
        "address": None,
        "stars": None,
        "check_in_time": None,
        "check_out_time": None,
        "description": None,
        "gallery": [],
        "facilities": [],
        "policies": {},
        "original_url": "https://www.it.lastminute.com/hotel/x/x/property_hid-20344",
        "location": None,
        "total_room_options": 0,
        "rooms": [],
        "details_status": "partial",
        "partial": True,
    }


@pytest.mark.asyncio
async def test_property_details_returns_partial_payload_for_expired_search_session():
    mcp = FakeMcp({
        "success": False,
        "error": "Search session expired",
        "pricing_id": "MUST-NOT-LEAK",
    })

    out = await property_details(
        hotel_id=77,
        search_id=999,
        date_from="2026-09-01",
        date_to="2026-09-05",
        user=object(),
        mcp=mcp,
    )

    assert out["id"] == 77
    assert out["details_status"] == "partial"
    assert out["partial"] is True
    assert out["rooms"] == []
    assert out["location"] is None
    assert out["original_url"].endswith("property_hid-77")
    assert "MUST-NOT-LEAK" not in json.dumps(out)


@pytest.mark.asyncio
async def test_partial_payload_survives_original_url_resolver_failure(monkeypatch):
    async def broken_resolver(hotel_id):
        raise RuntimeError("reader unavailable")

    monkeypatch.setattr(properties, "resolve_public_property_url", broken_resolver)
    mcp = FakeMcp({"success": False, "error": "Search session expired"})

    out = await property_details(
        hotel_id=12978711,
        search_id=999,
        date_from="2026-09-01",
        date_to="2026-09-05",
        user=object(),
        mcp=mcp,
    )

    assert out["details_status"] == "partial"
    assert out["partial"] is True
    assert out["original_url"] is None
    assert out["rooms"] == []


@pytest.mark.asyncio
async def test_property_details_exposes_all_public_features_and_provider_coordinates(monkeypatch):
    async def no_geocode(*args):
        raise AssertionError("provider coordinates must bypass Nominatim")

    monkeypatch.setattr(properties, "_geocode_property", no_geocode)
    mcp = FakeMcp({
        "success": True,
        "hotel": {
            "id": 88,
            "name": "Hotel Mappa",
            "address": "Via Roma 10",
            "latitude": "45.4642",
            "longitude": "9.1900",
            "facilities": ["Piscina", "Wi-Fi", "Piscina", ""],
        },
        "policies": {
            "wifi_free": True,
            "pets_allowed": False,
            "languages": ["it", "en"],
            "internal": {"secret": True},
        },
        "total_room_options": 2,
        "room_options": [
            {"room_name": "Classic", "price": 100, "currency": "EUR"},
            {"room_name": "Suite", "price": 180, "currency": "EUR"},
        ],
    })
    out = await property_details(
        hotel_id=88, search_id=999, date_from="2026-09-01", date_to="2026-09-05",
        destination="Milano", user=object(), mcp=mcp,
    )
    assert out["facilities"] == ["Piscina", "Wi-Fi"]
    assert out["policies"] == {
        "wifi_free": True, "pets_allowed": False, "languages": ["it", "en"],
    }
    assert out["location"] == {
        "lat": 45.4642, "lng": 9.19, "label": "Via Roma 10",
        "source": "provider", "confidence": 1.0,
    }
    assert out["total_room_options"] == 2
    assert [room["name"] for room in out["rooms"]] == ["Classic", "Suite"]


class MemoryRedis:
    def __init__(self):
        self.values = {}
        self.set_calls = []

    async def get(self, key):
        return self.values.get(key)

    async def set(self, key, value, ex=None):
        self.values[key] = value
        self.set_calls.append((key, value, ex))


@pytest.mark.asyncio
async def test_geocoder_uses_identifiable_cached_single_result_request(monkeypatch):
    redis = MemoryRedis()
    seen = {"clients": [], "gets": []}

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return [{
                "lat": "45.4642", "lon": "9.1900", "type": "house",
                "display_name": "Via Roma 10, Milano, Lombardia, Italia",
            }]

    class Client:
        def __init__(self, **kwargs):
            seen["clients"].append(kwargs)

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def get(self, url, params):
            seen["gets"].append((url, params))
            return Response()

    monkeypatch.setattr(properties, "get_redis", lambda: redis)
    monkeypatch.setattr(properties.httpx, "AsyncClient", Client)
    monkeypatch.setattr(properties, "_GEOCODE_SPACING_SECONDS", 0)
    monkeypatch.setattr(properties, "_last_geocode_at", 0.0)

    first = await properties._geocode_property("Via Roma 10", "Milano")
    second = await properties._geocode_property("Via Roma 10", "Milano")

    assert first == second
    assert first["source"] == "nominatim"
    assert len(seen["gets"]) == 1  # second lookup is served from Redis
    _, params = seen["gets"][0]
    assert params == {
        "q": "Via Roma 10, Milano", "format": "jsonv2", "limit": 1, "addressdetails": 1,
    }
    assert "TravelAgent" in seen["clients"][0]["headers"]["User-Agent"]
    assert redis.set_calls[0][2] == properties._GEOCODE_TTL


@pytest.mark.asyncio
async def test_geocoder_uses_property_name_when_search_destination_is_too_broad(monkeypatch):
    redis = MemoryRedis()
    seen = []

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return [{
                "lat": "32.6431386",
                "lon": "-16.8518121",
                "type": "hotel",
                "display_name": (
                    "Dom Pedro, 131, Estrada do Garajau, Caniço, Santa Cruz, Portogallo"
                ),
                "address": {
                    "road": "Estrada do Garajau",
                    "house_number": "131",
                    "town": "Caniço",
                },
            }]

    class Client:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def get(self, url, params):
            seen.append(params)
            return Response()

    monkeypatch.setattr(properties, "get_redis", lambda: redis)
    monkeypatch.setattr(properties.httpx, "AsyncClient", Client)
    monkeypatch.setattr(properties, "_GEOCODE_SPACING_SECONDS", 0)
    monkeypatch.setattr(properties, "_last_geocode_at", 0.0)

    location = await properties._geocode_property(
        "Estrada do Garajau, 131",
        "Funchal",
        "Garajau Madeira Hotel",
    )

    assert location["lat"] == 32.6431386
    assert location["lng"] == -16.8518121
    assert seen[0]["q"] == "Garajau Madeira Hotel, Estrada do Garajau, 131"


@pytest.mark.asyncio
async def test_geocoder_never_queries_a_generic_city(monkeypatch):
    class BoomClient:
        def __init__(self, **kwargs):
            raise AssertionError("generic city must not be sent to Nominatim")

    monkeypatch.setattr(properties.httpx, "AsyncClient", BoomClient)
    assert await properties._geocode_property("Roma", "Roma") is None


@pytest.mark.parametrize("result", [
    {
        "lat": "45.47", "lon": "9.18", "type": "house",
        "display_name": "Via Torino 10, Milano, Lombardia, Italia",
        "address": {"road": "Via Torino", "house_number": "10", "city": "Milano"},
    },
    {
        "lat": "45.48", "lon": "9.20", "type": "house",
        "display_name": "Piazza Roma 99, Milano, Lombardia, Italia",
        "address": {"road": "Piazza Roma", "house_number": "99", "city": "Milano"},
    },
])
def test_geocoder_rejects_wrong_street_or_house_number_for_specific_address(result):
    assert not properties._confident_geocode(result, "Via Roma 10", "Milano")


def test_geocoder_accepts_matching_street_and_house_number():
    result = {
        "lat": "45.4642", "lon": "9.1900", "type": "house",
        "display_name": "Via Roma 10, Milano, Lombardia, Italia",
        "address": {"road": "Via Roma", "house_number": "10", "city": "Milano"},
    }
    assert properties._confident_geocode(result, "Via Roma 10", "Milano")


def test_geocoder_validates_civic_number_after_comma_without_broad_destination_match():
    result = {
        "lat": "32.6431",
        "lon": "-16.8518",
        "type": "hotel",
        "display_name": "Estrada do Garajau 999, Caniço, Portogallo",
        "address": {"road": "Estrada do Garajau", "house_number": "999"},
    }
    assert not properties._confident_geocode(
        result,
        "Estrada do Garajau, 131",
        "Funchal",
        require_destination=False,
    )
