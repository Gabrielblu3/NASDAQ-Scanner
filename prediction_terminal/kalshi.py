"""Kalshi adapter — trade-api v2 (public market data, no auth for reads).

HOST RESOLUTION (validated 2026-07-18): `api.kalshi.com` does not exist in DNS —
it was never a network block. The legacy `trading-api.kalshi.com` responds with
"API has been moved to https://api.elections.kalshi.com/". The elections host IS
production; there is no other host to flip to. Fed/macro series (KXFED,
KXFEDDECISION) live there with live two-sided `_dollars` books — the earlier
"only illiquid combos" read came from fetching the first N markets unfiltered.
Use `series_ticker` / `event_ticker` to target the series worth cross-matching.

Two price schemas exist across hosts and this adapter handles BOTH:
  - production `api.kalshi.com`: `yes_bid`/`yes_ask`/`last_price` in integer CENTS (0-100).
  - elections host: `yes_bid_dollars`/`yes_ask_dollars`/`last_price_dollars` in DOLLARS (0-1).
Implied prob prefers the bid/ask midpoint, falls back to last price, and normalizes both to 0-1.
"""

from __future__ import annotations

import json
from typing import List, Optional
from urllib.request import urlopen, Request
from urllib.parse import urlencode

from models import NormalizedMarket

# Production host (see HOST RESOLUTION above — this is the only live host).
KALSHI_BASE = "https://api.elections.kalshi.com"


def _get(path: str, params: dict) -> dict:
    url = f"{KALSHI_BASE}{path}?{urlencode(params)}"
    req = Request(url, headers={"User-Agent": "prediction-terminal/0.2"})
    with urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode())


def _num(v) -> Optional[float]:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f


def _implied_prob(m: dict) -> Optional[float]:
    # Elections-host schema: *_dollars already in 0-1.
    bid_d, ask_d = _num(m.get("yes_bid_dollars")), _num(m.get("yes_ask_dollars"))
    if bid_d and ask_d:                # both non-zero -> live two-sided quote
        return (bid_d + ask_d) / 2.0
    last_d = _num(m.get("last_price_dollars"))
    if last_d:
        return last_d
    # Production-host schema: cents (0-100).
    bid_c, ask_c = _num(m.get("yes_bid")), _num(m.get("yes_ask"))
    if bid_c and ask_c:
        return (bid_c + ask_c) / 200.0
    last_c = _num(m.get("last_price"))
    if last_c:
        return last_c / 100.0
    return None


def fetch_markets(limit: int = 200) -> List[NormalizedMarket]:
    """Fetch open markets. Skeleton keeps only priced markets (dropped illiquid combos)."""
    data = _get("/trade-api/v2/markets", {"limit": limit, "status": "open"})
    out: List[NormalizedMarket] = []
    for m in data.get("markets", []):
        prob = _implied_prob(m)
        if prob is None:
            continue
        title = m.get("title") or m.get("yes_sub_title") or ""
        out.append(NormalizedMarket(
            venue="kalshi",
            market_id=m.get("ticker", "") or "",
            event_title=title,
            outcome="Yes",
            implied_prob=prob,
            resolution_criteria=m.get("rules_primary", "") or "",
            settlement_source="",       # Kalshi encodes source inside rules_primary
            close_time=m.get("close_time", "") or "",
            volume_usd=_to_float(m.get("volume_fp", m.get("volume"))),
            liquidity_usd=_to_float(m.get("liquidity_dollars",
                                          m.get("open_interest"))),
            raw=m,
        ))
    return out


def _to_float(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


if __name__ == "__main__":
    ms = fetch_markets(limit=200)
    print(f"kalshi ({KALSHI_BASE}): {len(ms)} priced markets")
    for m in ms[:5]:
        print(f"  {m.implied_prob:>5.2f}  {m.event_title[:70]}")
