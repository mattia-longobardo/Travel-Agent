"""Parse prices from the lastminute MCP, which serialises them as localized
strings such as "266,54 €" or "1.266,54 €" (European thousands "." + decimal ",")."""

import re


def parse_price(value) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if not isinstance(value, str):
        return None
    s = re.sub(r"[^0-9.,-]", "", value.strip())
    if not s or s in ("-", ".", ","):
        return None
    if "," in s:
        # European format: "." is the thousands separator, "," the decimal.
        s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None
