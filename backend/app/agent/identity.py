"""Defensive identity extraction for loosely-versioned lastminute payloads."""

from collections.abc import Mapping


_SEARCH_ID_KEYS = ("search_id", "vcSearchId", "vc_search_id")
_HOTEL_ID_KEYS = ("internal_id_hotel", "hotel_internal_id", "hotel_id")
_HOTEL_CONTAINERS = ("hotel", "accommodation", "property")


def _present(value):
    return value is not None and value != ""


def _find_key(value, keys, *, skip_keys=()):
    """Depth-first lookup for known unambiguous keys in dict/list payload fragments."""
    if isinstance(value, Mapping):
        for key in keys:
            candidate = value.get(key)
            if _present(candidate):
                return candidate
        for key, nested in value.items():
            if key in skip_keys:
                continue
            candidate = _find_key(nested, keys, skip_keys=skip_keys)
            if _present(candidate):
                return candidate
    elif isinstance(value, list):
        for nested in value:
            candidate = _find_key(nested, keys, skip_keys=skip_keys)
            if _present(candidate):
                return candidate
    return None


def extract_search_id(top_level, item):
    """Prefer the item's search identity, then fall back to the response-level identity."""
    candidate = _find_key(item, _SEARCH_ID_KEYS)
    if _present(candidate):
        return candidate
    if isinstance(item, Mapping):
        search = item.get("search")
        if isinstance(search, Mapping) and _present(search.get("id")):
            return search["id"]

    if isinstance(top_level, Mapping):
        # Do not descend into result collections: otherwise an item missing search_id could
        # accidentally inherit a sibling offer's id instead of the response-level id.
        candidate = _find_key(
            top_level, _SEARCH_ID_KEYS,
            skip_keys=("products_summary", "results", "hotels", "packages"),
        )
        if _present(candidate):
            return candidate
        search = top_level.get("search")
        if isinstance(search, Mapping) and _present(search.get("id")):
            return search["id"]
    return None


def extract_hotel_id(item, *, allow_item_id: bool = False):
    """Read a hotel id from direct or nested hotel/accommodation/property objects.

    A generic top-level item ``id`` is accepted only for hotel-search results. In a package
    result it can identify the package itself, so package callers leave ``allow_item_id=False``.
    """
    candidate = _find_key(item, _HOTEL_ID_KEYS)
    if _present(candidate):
        return candidate
    if not isinstance(item, Mapping):
        return None
    for key in _HOTEL_CONTAINERS:
        nested = item.get(key)
        if isinstance(nested, Mapping) and _present(nested.get("id")):
            return nested["id"]
    if allow_item_id and _present(item.get("id")):
        return item["id"]
    return None


def extract_destination_code(top_level, item):
    """Read the lastminute destination code from a response/item search_params object."""
    for value in (item, top_level):
        if not isinstance(value, Mapping):
            continue
        params = value.get("search_params")
        if isinstance(params, Mapping) and _present(params.get("destination")):
            return params["destination"]
        search = value.get("search")
        if isinstance(search, Mapping):
            params = search.get("search_params") or search.get("params")
            if isinstance(params, Mapping) and _present(params.get("destination")):
                return params["destination"]
    return None
