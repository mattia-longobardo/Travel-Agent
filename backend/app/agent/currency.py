"""Currency normalization shared by lastminute offer adapters."""

from collections.abc import Mapping


EUR = "EUR"


def offer_currency(item, top_level=None) -> str:
    """Return the item currency, then response currency, defaulting legacy payloads to EUR.

    Item-level metadata is more specific and therefore wins when both are present. Older MCP
    payloads omitted currency entirely while the application only searched the Italian/EUR
    storefront; those payloads remain compatible by treating a missing value as EUR.
    """
    for value in (item, top_level):
        if not isinstance(value, Mapping):
            continue
        currency = value.get("currency")
        if currency not in (None, ""):
            return str(currency).strip().upper()
    return EUR


def is_eur_offer(item, top_level=None) -> bool:
    return offer_currency(item, top_level) == EUR
