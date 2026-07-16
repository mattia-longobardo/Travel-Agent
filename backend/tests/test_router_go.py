import pytest

from app.agent.links import HOTEL_FALLBACK_URL
from app.routers import go


@pytest.mark.asyncio
async def test_go_hotel_redirects_only_to_public_provider_property_page():
    public = (
        "https://www.it.lastminute.com/hotel/portogallo/santa-cruz/"
        "dom-pedro-garajau_hid-20344"
    )
    response = await go.go_hotel(property_url=public)
    assert response.status_code == 302
    assert response.headers["location"] == public


@pytest.mark.asyncio
@pytest.mark.parametrize("url", [
    "",
    "http://www.lastminute.com/hotel/italia/roma/example_hid-7",
    "https://evil.example/hotel/italia/roma/example_hid-7",
    "https://lastminute.com.evil.example/hotel/italia/roma/example_hid-7",
    "https://www.lastminute.com/s/tsx/7?pageType=review",
    "https://www.lastminute.com/s/tsx/7?pageType=review&pricingId=SECRET",
    "https://www.lastminute.com/hotel/italia/roma/example",
    "https://www.lastminute.com/hotel/example_hid-7",
    "https://www.lastminute.com/booking/checkout-123",
])
async def test_go_hotel_rejects_non_public_or_checkout_urls(url):
    response = await go.go_hotel(property_url=url)
    assert response.status_code == 302
    assert response.headers["location"] == HOTEL_FALLBACK_URL


def test_safe_property_url_accepts_only_italian_storefront_and_drops_query():
    url = "https://www.it.lastminute.com/hotel/italia/roma/example_hid-7/?tracking=x"
    assert go._safe_property_url(url) == (
        "https://www.it.lastminute.com/hotel/italia/roma/example_hid-7"
    )
    assert go._safe_property_url(
        "https://lastminute.com/hotel/italia/roma/example_hid-7"
    ) is None
