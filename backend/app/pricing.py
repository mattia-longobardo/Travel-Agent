"""OpenAI API token pricing, USD per 1,000,000 tokens.

OpenAI exposes no pricing API, so prices are scraped at runtime from the
official pricing page (https://developers.openai.com/api/docs/pricing) and
cached to disk; ``FALLBACK_PRICING`` seeds the table and keeps costing working
when the page is unreachable or a model disappears from it.
Telemetry does not track cached-input tokens, so the full input rate is applied
to prompt_tokens (a slight overestimate); cost is an estimate.
"""
from __future__ import annotations

import json
import logging
import re
import tempfile
import time
from html.parser import HTMLParser
from pathlib import Path

import httpx

log = logging.getLogger(__name__)

PRICING_URL = "https://developers.openai.com/api/docs/pricing"
CACHE_FILE = Path(tempfile.gettempdir()) / "openai_pricing_cache.json"
CACHE_TTL_SECONDS = 24 * 3600

# Snapshot of the pricing page, last verified 2026-07-16.
FALLBACK_PRICING: dict[str, dict] = {
    "gpt-5.6-sol": {"input": 5.00, "output": 30.00},
    "gpt-5.6-terra": {"input": 2.50, "output": 15.00},
    "gpt-5.6-luna": {"input": 1.00, "output": 6.00},
    "gpt-5.5": {"input": 5.00, "output": 30.00},
    "gpt-5.5-pro": {"input": 30.00, "output": 180.00},
    "gpt-5.4": {"input": 2.50, "output": 15.00},
}

# Live table used by cost_usd and the admin analytics queries. Updated in
# place by refresh_pricing() so importers always see current rates.
MODEL_PRICING: dict[str, dict] = {k: dict(v) for k, v in FALLBACK_PRICING.items()}

_MODEL_RE = re.compile(r"[a-z0-9][a-z0-9.\-]*")
_PRICE_RE = re.compile(r"\$(\d+(?:\.\d+)?)")


class _TableParser(HTMLParser):
    """Collects every <table> as a list of rows of stripped cell texts."""

    def __init__(self):
        super().__init__()
        self.tables: list[list[list[str]]] = []
        self._table: list[list[str]] | None = None
        self._row: list[str] | None = None
        self._cell: str | None = None

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            self._table = []
        elif tag == "tr" and self._table is not None:
            self._row = []
        elif tag in ("td", "th") and self._row is not None:
            self._cell = ""

    def handle_endtag(self, tag):
        if tag == "table" and self._table is not None:
            self.tables.append(self._table)
            self._table = None
        elif tag == "tr" and self._row is not None:
            self._table.append(self._row)
            self._row = None
        elif tag in ("td", "th") and self._cell is not None:
            self._row.append(self._cell.strip())
            self._cell = None

    def handle_data(self, data):
        if self._cell is not None:
            self._cell += data


def _price(cell: str) -> float | None:
    m = _PRICE_RE.fullmatch(cell.strip())
    return float(m.group(1)) if m else None


def parse_pricing_html(html: str) -> dict[str, dict]:
    """Extract {model: {input, output}} (USD per 1M tokens) from the page.

    The page repeats the same table shape for standard, batch and priority
    tiers in that order; keeping the first occurrence of each model yields the
    standard tier (and the short-context rate for context-tiered rows).
    """
    parser = _TableParser()
    parser.feed(html)
    prices: dict[str, dict] = {}
    for table in parser.tables:
        header = next((row for row in table if "Model" in row), None)
        if header is None or "Input" not in header or "Output" not in header:
            continue
        m_i, in_i = header.index("Model"), header.index("Input")
        out_i = header.index("Output")
        for row in table[table.index(header) + 1:]:
            # Cells swallowed by a rowspan in a leading column shift the row.
            shift = len(header) - len(row)
            if shift < 0 or m_i - shift < 0 or out_i - shift >= len(row):
                continue
            name = row[m_i - shift].split(" (")[0].strip()
            if not _MODEL_RE.fullmatch(name) or name in prices:
                continue
            inp, out = _price(row[in_i - shift]), _price(row[out_i - shift])
            if inp is None or out is None:
                continue
            prices[name] = {"input": inp, "output": out}
    if len(prices) < 3:
        raise ValueError("pricing page yielded too few models; layout changed?")
    return prices


def _load_cache() -> dict | None:
    try:
        data = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        if isinstance(data.get("prices"), dict) and isinstance(data.get("fetched_at"), (int, float)):
            return data
    except (OSError, ValueError):
        pass
    return None


def _save_cache(prices: dict[str, dict]) -> None:
    payload = {"fetched_at": time.time(), "url": PRICING_URL, "prices": prices}
    try:
        CACHE_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    except OSError as exc:
        log.warning("could not write pricing cache %s: %s", CACHE_FILE, exc)


def refresh_pricing(force: bool = False) -> bool:
    """Bring MODEL_PRICING up to date; returns True when live data was fetched.

    Uses the on-disk cache while fresh; otherwise scrapes the pricing page.
    On any failure the newest data available (stale cache, then fallback
    snapshot) stays in effect. Blocking — call via asyncio.to_thread from
    async code.
    """
    cache = _load_cache()
    if cache and not force and time.time() - cache["fetched_at"] < CACHE_TTL_SECONDS:
        MODEL_PRICING.update(cache["prices"])
        return False
    try:
        resp = httpx.get(PRICING_URL, headers={"User-Agent": "Mozilla/5.0"},
                         timeout=30, follow_redirects=True)
        resp.raise_for_status()
        prices = parse_pricing_html(resp.text)
    except (httpx.HTTPError, ValueError) as exc:
        log.warning("pricing refresh failed (%s); keeping %s prices",
                    exc, "cached" if cache else "fallback")
        if cache:
            MODEL_PRICING.update(cache["prices"])
        return False
    if cache and prices != cache["prices"]:
        log.info("OpenAI pricing changed since last fetch")
    MODEL_PRICING.update(prices)
    _save_cache(prices)
    return True


def cost_usd(model: str | None, prompt_tokens: int, completion_tokens: int) -> float | None:
    price = MODEL_PRICING.get(model or "")
    if price is None:
        return None
    return round(prompt_tokens / 1_000_000 * price["input"]
                 + completion_tokens / 1_000_000 * price["output"], 6)
