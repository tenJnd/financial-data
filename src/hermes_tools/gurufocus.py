"""Anonymous GuruFocus summary scrape.

GuruFocus blocks plain requests with Cloudflare; curl_cffi with Chrome TLS
fingerprinting passes through. Insider trades and guru trades on the public
/summary page are paywalled and are intentionally not parsed here — the user
already gets the insider signal from finviz columns, and guru trades require
a Premium subscription.
"""
from __future__ import annotations

import re
from typing import Any

from bs4 import BeautifulSoup
from curl_cffi import requests

SUMMARY_URL = "https://www.gurufocus.com/stock/{ticker}/summary"
DEFAULT_TIMEOUT = 30
IMPERSONATE = "chrome"

_NUMERIC_RE = re.compile(r"^-?\$?\s*[\d,]+(?:\.\d+)?%?$")


class GuruFocusBlocked(RuntimeError):
    """Raised when GuruFocus returns a Cloudflare challenge / 403."""


def _fetch(ticker: str) -> str:
    url = SUMMARY_URL.format(ticker=ticker.upper())
    r = requests.get(url, impersonate=IMPERSONATE, timeout=DEFAULT_TIMEOUT)
    if r.status_code != 200:
        raise GuruFocusBlocked(f"{url} -> {r.status_code}")
    if "Just a moment..." in r.text or "cf-browser-verification" in r.text:
        raise GuruFocusBlocked(f"{url} -> Cloudflare challenge")
    return r.text


def _to_snake(label: str) -> str:
    s = label.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    return s.strip("_")


def _coerce(value: str) -> Any:
    v = value.strip()
    if not v or v == "-":
        return None
    if _NUMERIC_RE.match(v):
        clean = v.replace("$", "").replace(",", "").replace("%", "").strip()
        try:
            n = float(clean)
            return int(n) if n.is_integer() and "." not in clean else n
        except ValueError:
            return v
    return v


def parse_summary(html: str) -> dict[str, Any]:
    soup = BeautifulSoup(html, "lxml")
    metrics: dict[str, Any] = {}
    for td in soup.select("td.semi-bold"):
        label = td.get_text(" ", strip=True)
        nxt = td.find_next_sibling("td")
        if not label or not nxt:
            continue
        raw = nxt.get_text(" ", strip=True)
        key = _to_snake(label)
        if not key:
            continue
        metrics[key] = _coerce(raw)
    return metrics


def fetch_gurufocus_summary(ticker: str) -> dict[str, Any]:
    html = _fetch(ticker)
    metrics = parse_summary(html)
    return {
        "ticker": ticker.upper(),
        "source_url": SUMMARY_URL.format(ticker=ticker.upper()),
        "metrics": metrics,
        "premium_only_sections": ["insider_trades", "guru_trades"],
    }
