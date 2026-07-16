"""Deterministic redirect to an allowlisted public lastminute property page."""
from fastapi import APIRouter, Query
from fastapi.responses import RedirectResponse

from app.agent.links import HOTEL_FALLBACK_URL
from app.property_urls import safe_public_property_url

router = APIRouter(prefix="/api/go", tags=["go"])

_DEFAULT = HOTEL_FALLBACK_URL


def _safe_property_url(url: str | None) -> str | None:
    """Allow only public ``/hotel/..._hid-ID`` pages; ``/s/tsx`` is a sales funnel."""
    return safe_public_property_url(url)


@router.get("/hotel")
async def go_hotel(property_url: str = Query("")):
    # No checkout fallback: either the details page carries an exact public provider URL or the
    # user lands on the provider's safe hotel section.
    return RedirectResponse(_safe_property_url(property_url) or _DEFAULT, status_code=302)
