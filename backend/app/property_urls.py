"""Resolve public lastminute hotel-detail pages from provider hotel IDs.

The MCP currently exposes the hotel ID and presentation data, but not the public SEO URL.
lastminute's public hotel page is keyed by the ``_hid-<id>`` suffix; the preceding country,
city and slug segments are descriptive.  We use a fixed-host neutral URL to read the page and
recover its canonical public permalink. If lastminute has no public hotel-detail page for that
inventory item, the resolver returns ``None`` so the UI does not label a 404 as "original site".

No caller-provided URL is ever fetched here.  This is intentional: it keeps the resolver from
becoming an SSRF primitive and ensures that a temporary resolver failure can never send the user
to the dated ``/s/tsx`` sales funnel.
"""

import html
import os
import re
from urllib.parse import urlparse

import httpx

from app.redis_client import get_redis

_LASTMINUTE_ORIGIN = "https://www.it.lastminute.com"
_LASTMINUTE_HOST = "www.it.lastminute.com"
_READER_ORIGIN = os.getenv("TRAVEL_PROPERTY_READER_URL", "https://r.jina.ai").rstrip("/")
_RESOLVE_TIMEOUT_SECONDS = 8.0
_CANONICAL_TTL_SECONDS = 60 * 60 * 24 * 30
_NEGATIVE_TTL_SECONDS = 60 * 60
_MAX_READER_BYTES = 1_000_000

_PUBLIC_PATH = re.compile(
    r"^/hotel/(?:[^/?#]+/){2}[^/?#]+_hid-(?P<hotel_id>\d+)/?$",
    re.IGNORECASE,
)


def public_property_lookup_url(hotel_id: int) -> str:
    """Return the neutral public route used only to ask the reader for page metadata."""
    return f"{_LASTMINUTE_ORIGIN}/hotel/x/x/property_hid-{int(hotel_id)}"


def safe_public_property_url(url: str | None, *, hotel_id: int | None = None) -> str | None:
    """Accept only Italian lastminute public hotel pages, optionally for one exact hotel ID."""
    if not isinstance(url, str) or not url:
        return None
    try:
        parsed = urlparse(url)
    except Exception:
        return None
    try:
        unexpected_authority = (
            parsed.username is not None
            or parsed.password is not None
            or parsed.port is not None
        )
    except ValueError:  # malformed ports (for example ``:not-a-port``)
        return None
    if (
        parsed.scheme != "https"
        or (parsed.hostname or "").lower().rstrip(".") != _LASTMINUTE_HOST
        or unexpected_authority
    ):
        return None
    match = _PUBLIC_PATH.fullmatch(parsed.path)
    if not match:
        return None
    resolved_id = int(match.group("hotel_id"))
    if hotel_id is not None and resolved_id != int(hotel_id):
        return None
    # Queries/fragments are unnecessary on the public presentation page. Dropping them also
    # prevents checkout or tracking state from leaking into the "Sito originale" action.
    return f"{_LASTMINUTE_ORIGIN}{parsed.path.rstrip('/')}"


def _extract_canonical_url(document: str, hotel_id: int) -> str | None:
    """Extract a strict same-property public permalink from the rendered page text."""
    if not isinstance(document, str):
        return None
    decoded = html.unescape(document)
    pattern = re.compile(
        rf"https://www\.it\.lastminute\.com/hotel/[^\s<>()\[\]\"']+_hid-{int(hotel_id)}/?",
        re.IGNORECASE,
    )
    candidates: list[str] = []
    for match in pattern.finditer(decoded):
        candidate = safe_public_property_url(match.group(0), hotel_id=hotel_id)
        if candidate and candidate not in candidates:
            candidates.append(candidate)
    if not candidates:
        return None
    # Prefer a descriptive permalink over our neutral resolver path if both are present.
    return min(candidates, key=lambda value: ("/hotel/x/x/" in value.lower(), len(value)))


def _canonical_from_reader(payload: object, hotel_id: int) -> str | None:
    """Read the verified Italian canonical only from a successful public HDP response."""
    if not isinstance(payload, dict):
        return None
    data = payload.get("data")
    if not isinstance(data, dict) or data.get("httpStatus") != 200:
        return None

    candidates: list[str] = []
    metadata = data.get("metadata")
    if isinstance(metadata, dict):
        og_url = metadata.get("og:url")
        if isinstance(og_url, str):
            candidates.append(og_url)
    external = data.get("external")
    if isinstance(external, dict) and isinstance(external.get("canonical"), dict):
        candidates.extend(external["canonical"].keys())
    for candidate in candidates:
        safe = safe_public_property_url(candidate, hotel_id=hotel_id)
        if safe:
            return safe

    # Older reader responses may omit metadata but still include the canonical among the
    # rendered links. This remains constrained to the same host and exact HID.
    return _extract_canonical_url(data.get("content"), hotel_id)


def _cache_key(hotel_id: int) -> str:
    # v2 distinguishes a verified canonical from the old neutral-path fallback cache.
    return f"property-public-url:v2:{int(hotel_id)}"


async def _cached_url(hotel_id: int) -> tuple[bool, str | None]:
    try:
        value = await get_redis().get(_cache_key(hotel_id))
    except Exception:
        return False, None
    if value is None:
        return False, None
    if isinstance(value, bytes):
        value = value.decode(errors="ignore")
    if value == "null":
        return True, None
    safe = safe_public_property_url(value, hotel_id=hotel_id)
    return (True, safe) if safe else (False, None)


async def _cache_url(hotel_id: int, url: str | None) -> None:
    try:
        await get_redis().set(
            _cache_key(hotel_id),
            url or "null",
            ex=_CANONICAL_TTL_SECONDS if url else _NEGATIVE_TTL_SECONDS,
        )
    except Exception:
        pass


async def resolve_public_property_url(hotel_id: int) -> str | None:
    """Resolve a verified canonical public page, or ``None`` when no HDP can be verified."""
    hotel_id = int(hotel_id)
    if hotel_id <= 0:
        raise ValueError("hotel_id must be positive")
    found, cached = await _cached_url(hotel_id)
    if found:
        return cached

    canonical = None
    # Jina Reader renders the Cloudflare-protected public page and returns its public links.
    # The target is assembled solely from the validated integer ID; callers cannot influence
    # either host. A tight timeout and response-size cap keep this an optional enrichment.
    lookup_url = public_property_lookup_url(hotel_id)
    reader_target = lookup_url.removeprefix("https://")
    reader_url = f"{_READER_ORIGIN}/http://{reader_target}"
    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(_RESOLVE_TIMEOUT_SECONDS),
            follow_redirects=False,
            headers={
                "User-Agent": "TravelAgent/1.0 (https://travel.longobardo.me)",
                "Accept": "application/json",
            },
        ) as client:
            response = await client.get(reader_url)
            response.raise_for_status()
            if len(response.content) <= _MAX_READER_BYTES:
                try:
                    payload = response.json()
                except Exception:
                    # Compatibility with reader deployments that still return plain Markdown.
                    canonical = _extract_canonical_url(response.text, hotel_id)
                else:
                    canonical = _canonical_from_reader(payload, hotel_id)
    except Exception:
        canonical = None

    await _cache_url(hotel_id, canonical)
    return canonical
