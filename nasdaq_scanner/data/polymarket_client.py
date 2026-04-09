"""Lightweight read-only client for the public Polymarket Gamma API."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Optional

import requests

GAMMA_MARKETS_URL = "https://gamma-api.polymarket.com/markets"


@dataclass
class PolyMarket:
    question: str
    slug: str
    end_date: str
    volume: float
    yes_price: float  # 0.0 – 1.0
    url: str


def _parse_outcome_prices(raw) -> Optional[list[float]]:
    if raw is None:
        return None
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError:
            return None
    if not isinstance(raw, list):
        return None
    try:
        return [float(x) for x in raw]
    except (TypeError, ValueError):
        return None


def _parse_outcomes(raw) -> Optional[list[str]]:
    if raw is None:
        return None
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError:
            return None
    if isinstance(raw, list):
        return [str(x) for x in raw]
    return None


def fetch_top_markets(limit: int = 5, tag: Optional[str] = None) -> list[PolyMarket]:
    """Fetch the top-volume active Polymarket markets. Returns [] on any failure."""
    params = {
        "active": "true",
        "closed": "false",
        "order": "volume",
        "ascending": "false",
        "limit": str(max(limit * 4, 20)),  # over-fetch; we filter to clean YES/NO markets
    }
    if tag:
        params["tag_slug"] = tag

    for attempt in range(2):
        try:
            resp = requests.get(GAMMA_MARKETS_URL, params=params, timeout=4)
            if resp.status_code != 200:
                return []
            data = resp.json()
            break
        except (requests.ConnectionError, requests.Timeout):
            if attempt == 1:
                return []
            continue
        except Exception:
            return []
    else:
        return []

    if not isinstance(data, list):
        return []

    out: list[PolyMarket] = []
    for m in data:
        try:
            outcomes = _parse_outcomes(m.get("outcomes"))
            prices = _parse_outcome_prices(m.get("outcomePrices"))
            if not outcomes or not prices or len(outcomes) != 2 or len(prices) != 2:
                continue
            if [o.lower() for o in outcomes] != ["yes", "no"]:
                continue
            slug = m.get("slug") or ""
            question = m.get("question") or ""
            if not slug or not question:
                continue
            volume = float(m.get("volume") or 0)
            end_date = m.get("endDate") or ""
            out.append(
                PolyMarket(
                    question=question,
                    slug=slug,
                    end_date=end_date,
                    volume=volume,
                    yes_price=prices[0],
                    url=f"https://polymarket.com/event/{slug}",
                )
            )
            if len(out) >= limit:
                break
        except Exception:
            continue

    return out
