"""Polymarket adapter — Gamma API (public, no auth).

Gamma quirks handled here:
  - `outcomes` / `outcomePrices` arrive as JSON-encoded *strings*, not lists.
  - For binary Yes/No markets the "Yes" outcomePrice already IS the implied prob.
  - Resolution criteria + settlement source live in free-text `description`.
"""

from __future__ import annotations

import json
import re
from typing import List
from urllib.request import urlopen, Request
from urllib.parse import urlencode

from models import NormalizedMarket

GAMMA_BASE = "https://gamma-api.polymarket.com"


def _get(path: str, params: dict) -> list | dict:
    url = f"{GAMMA_BASE}{path}?{urlencode(params)}"
    req = Request(url, headers={"User-Agent": "prediction-terminal/0.2"})
    with urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode())


def _parse_json_field(value) -> list:
    if isinstance(value, list):
        return value
    if isinstance(value, str) and value:
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return []
    return []


def _extract_source(description: str) -> str:
    if not description:
        return ""
    m = re.search(r"resolution source[^.]*\.", description, re.IGNORECASE)
    return m.group(0).strip() if m else ""


def fetch_markets(limit: int = 100) -> List[NormalizedMarket]:
    """Fetch active, open, binary markets ordered by volume (most liquid first)."""
    rows = _get(
        "/markets",
        {"limit": limit, "active": "true", "closed": "false",
         "order": "volume", "ascending": "false"},
    )
    if isinstance(rows, dict):          # some responses wrap in an object
        rows = rows.get("data", [])

    out: List[NormalizedMarket] = []
    for m in rows:
        outcomes = _parse_json_field(m.get("outcomes"))
        prices = _parse_json_field(m.get("outcomePrices"))
        if outcomes[:2] != ["Yes", "No"] or len(prices) < 1:
            continue                    # keep the skeleton to clean binary markets
        try:
            yes_prob = float(prices[0])
        except (TypeError, ValueError):
            continue
        desc = m.get("description", "") or ""
        out.append(NormalizedMarket(
            venue="polymarket",
            market_id=str(m.get("id", "")),
            event_title=m.get("question", "") or "",
            outcome="Yes",
            implied_prob=yes_prob,
            resolution_criteria=desc,
            settlement_source=_extract_source(desc),
            close_time=m.get("endDate", "") or "",
            volume_usd=_to_float(m.get("volume")),
            liquidity_usd=_to_float(m.get("liquidity")),
            raw=m,
        ))
    return out


def _to_float(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


if __name__ == "__main__":
    ms = fetch_markets(limit=25)
    print(f"polymarket: {len(ms)} binary markets")
    for m in ms[:5]:
        print(f"  {m.implied_prob:>5.2f}  {m.event_title[:70]}")
