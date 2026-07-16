"""Pull a usable image URL out of a raw MCP product item.

The lastminute payload shape isn't strongly documented, so we probe the field names it
is most likely to use (and nested hotel objects), returning the first http(s) URL found.
The frontend falls back to a destination stock image when this is None.
"""
from typing import Any

_KEYS = ("image_url", "image", "thumbnail", "photo", "picture", "cover", "main_image")
_LIST_KEYS = ("images", "photos", "pictures", "gallery", "media")


def _as_url(value: Any) -> str | None:
    if isinstance(value, str) and value.startswith(("http://", "https://")):
        return value
    if isinstance(value, dict):
        return _as_url(value.get("url") or value.get("src") or value.get("href"))
    return None


def first_image(item: dict) -> str | None:
    """Best-effort first image URL for a product item, or None."""
    if not isinstance(item, dict):
        return None
    for key in _KEYS:
        url = _as_url(item.get(key))
        if url:
            return url
    for key in _LIST_KEYS:
        seq = item.get(key)
        if isinstance(seq, list):
            for entry in seq:
                url = _as_url(entry)
                if url:
                    return url
    # Nested hotel object (packages embed the hotel under "hotel").
    nested = item.get("hotel")
    if isinstance(nested, dict):
        return first_image(nested)
    return None
