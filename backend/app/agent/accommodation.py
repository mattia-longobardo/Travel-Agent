"""Shared lastminute accommodation filters and request normalization."""

ACCOMMODATION_FILTERS = {
    "hotel": "1,2",
    "home": "3,6,7,9,14",
}


def requested_accommodation_kinds(value: str | None) -> list[str]:
    """Return one or both supported search kinds, defaulting safely to both."""
    if value in ACCOMMODATION_FILTERS:
        return [value]
    return list(ACCOMMODATION_FILTERS)
