import httpx
import pytest

import app.pricing as pricing
from app.pricing import (FALLBACK_PRICING, MODEL_PRICING, cost_usd,
                         parse_pricing_html, refresh_pricing)

# Mirrors the structure of developers.openai.com/api/docs/pricing: grouped
# header rows, standard tier before batch tier, context-length variants and
# Category tables with rowspans.
SAMPLE_HTML = """
<h2>Flagship models</h2>
<table>
  <tr><th></th><th colspan="4">Short context</th><th colspan="4">Long context</th></tr>
  <tr><th>Model</th><th>Input</th><th>Cached input</th><th>Cache writes</th><th>Output</th>
      <th>Input</th><th>Cached input</th><th>Cache writes</th><th>Output</th></tr>
  <tr><td>gpt-5.6-terra</td><td>$2.50</td><td>$0.25</td><td>$3.125</td><td>$15.00</td>
      <td>$5.00</td><td>$0.50</td><td>$6.25</td><td>$22.50</td></tr>
  <tr><td>gpt-5.5 (&lt;272K context length)</td><td>$5.00</td><td>$0.50</td><td>-</td><td>$30.00</td>
      <td>-</td><td>-</td><td>-</td><td>-</td></tr>
  <tr><td>gpt-5.5 (&gt;=272K context length)</td><td>$10.00</td><td>$1.00</td><td>-</td><td>$45.00</td>
      <td>-</td><td>-</td><td>-</td><td>-</td></tr>
</table>
<table>
  <tr><th></th><th colspan="4">Short context</th><th colspan="4">Long context</th></tr>
  <tr><th>Model</th><th>Input</th><th>Cached input</th><th>Cache writes</th><th>Output</th>
      <th>Input</th><th>Cached input</th><th>Cache writes</th><th>Output</th></tr>
  <tr><td>gpt-5.6-terra</td><td>$1.25</td><td>$0.125</td><td>$1.5625</td><td>$7.50</td>
      <td>$2.50</td><td>$0.25</td><td>$3.125</td><td>$11.25</td></tr>
</table>
<h2>Specialized models</h2>
<table>
  <tr><th>Category</th><th>Model</th><th>Input</th><th>Cached input</th><th>Output</th></tr>
  <tr><td rowspan="2">Deep research</td><td>o3-deep-research</td><td>$5.00</td><td>-</td><td>$20.00</td></tr>
  <tr><td>o4-mini-deep-research</td><td>$1.00</td><td>-</td><td>$4.00</td></tr>
  <tr><td>Cyber</td><td>gpt-5.4-cyber</td><td>-</td><td>-</td><td>-</td></tr>
</table>
"""


@pytest.fixture(autouse=True)
def _restore_model_pricing():
    snapshot = {k: dict(v) for k, v in MODEL_PRICING.items()}
    yield
    MODEL_PRICING.clear()
    MODEL_PRICING.update(snapshot)


def _response(html: str) -> httpx.Response:
    return httpx.Response(200, text=html,
                          request=httpx.Request("GET", pricing.PRICING_URL))


def test_known_model_cost():
    # 1M prompt @2.50 + 1M completion @15.00 = 17.50
    assert cost_usd("gpt-5.4", 1_000_000, 1_000_000) == 17.5
    assert "gpt-5.4" in MODEL_PRICING


def test_unknown_model_returns_none():
    assert cost_usd("mystery", 1000, 1000) is None
    assert cost_usd(None, 1000, 1000) is None


def test_parse_pricing_html():
    prices = parse_pricing_html(SAMPLE_HTML)
    # First (standard-tier) table wins over the batch table.
    assert prices["gpt-5.6-terra"] == {"input": 2.5, "output": 15.0}
    # Context-length suffix stripped; short-context row wins.
    assert prices["gpt-5.5"] == {"input": 5.0, "output": 30.0}
    # Rowspan in the Category column shifts the row but still parses.
    assert prices["o3-deep-research"] == {"input": 5.0, "output": 20.0}
    assert prices["o4-mini-deep-research"] == {"input": 1.0, "output": 4.0}
    # Rows without dollar prices are skipped.
    assert "gpt-5.4-cyber" not in prices


def test_parse_pricing_html_rejects_unexpected_layout():
    with pytest.raises(ValueError):
        parse_pricing_html("<p>no tables here</p>")


def test_refresh_pricing_fetches_and_caches(tmp_path, monkeypatch):
    monkeypatch.setattr(pricing, "CACHE_FILE", tmp_path / "cache.json")
    monkeypatch.setattr(pricing.httpx, "get", lambda *a, **k: _response(SAMPLE_HTML))
    assert refresh_pricing(force=True) is True
    assert MODEL_PRICING["gpt-5.6-terra"] == {"input": 2.5, "output": 15.0}
    # Fallback-only models survive a refresh that no longer lists them.
    assert MODEL_PRICING["gpt-5.6-luna"] == FALLBACK_PRICING["gpt-5.6-luna"]
    assert (tmp_path / "cache.json").exists()

    # A fresh cache short-circuits the network entirely.
    def _no_network(*a, **k):
        raise AssertionError("should not fetch while cache is fresh")
    monkeypatch.setattr(pricing.httpx, "get", _no_network)
    assert refresh_pricing() is False


def test_refresh_pricing_failure_keeps_current_prices(tmp_path, monkeypatch):
    monkeypatch.setattr(pricing, "CACHE_FILE", tmp_path / "missing.json")

    def _boom(*a, **k):
        raise httpx.ConnectError("no network")
    monkeypatch.setattr(pricing.httpx, "get", _boom)
    assert refresh_pricing(force=True) is False
    assert MODEL_PRICING["gpt-5.4"] == FALLBACK_PRICING["gpt-5.4"]


def test_refresh_pricing_falls_back_to_stale_cache(tmp_path, monkeypatch):
    cache_file = tmp_path / "cache.json"
    monkeypatch.setattr(pricing, "CACHE_FILE", cache_file)
    monkeypatch.setattr(pricing.httpx, "get", lambda *a, **k: _response(SAMPLE_HTML))
    refresh_pricing(force=True)

    def _boom(*a, **k):
        raise httpx.ConnectError("no network")
    monkeypatch.setattr(pricing.httpx, "get", _boom)
    MODEL_PRICING["gpt-5.6-terra"] = {"input": 0.0, "output": 0.0}
    assert refresh_pricing(force=True) is False
    assert MODEL_PRICING["gpt-5.6-terra"] == {"input": 2.5, "output": 15.0}
