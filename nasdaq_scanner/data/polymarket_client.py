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
    volume_24h: float = 0.0
    liquidity: float = 0.0
    one_day_change: float = 0.0  # 24h change in YES price, -1.0 – 1.0
    best_bid: Optional[float] = None
    best_ask: Optional[float] = None
    last_trade: Optional[float] = None
    description: str = ""
    category: str = ""

    @property
    def no_price(self) -> float:
        return max(0.0, 1.0 - self.yes_price)

    @property
    def spread(self) -> Optional[float]:
        if self.best_bid is None or self.best_ask is None:
            return None
        return max(0.0, self.best_ask - self.best_bid)


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


def _to_float(raw, default: float = 0.0) -> float:
    try:
        return float(raw)
    except (TypeError, ValueError):
        return default


def _to_float_or_none(raw) -> Optional[float]:
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def _extract_category(m: dict) -> str:
    events = m.get("events")
    if isinstance(events, list) and events and isinstance(events[0], dict):
        title = events[0].get("title")
        if title:
            return str(title).strip()
    return str(m.get("category") or "").strip()


def fetch_top_markets(
    limit: int = 10,
    tag: Optional[str] = None,
    order: str = "volume24hr",
) -> list[PolyMarket]:
    """Fetch the top active Polymarket markets by 24h trading volume.

    Returns [] on any failure.
    """
    params = {
        "active": "true",
        "closed": "false",
        "order": order,
        "ascending": "false",
        "limit": str(max(limit * 4, 40)),  # over-fetch; we filter to clean YES/NO markets
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
            out.append(
                PolyMarket(
                    question=question,
                    slug=slug,
                    end_date=m.get("endDate") or "",
                    volume=_to_float(m.get("volume")),
                    yes_price=prices[0],
                    url=f"https://polymarket.com/event/{slug}",
                    volume_24h=_to_float(m.get("volume24hr")),
                    liquidity=_to_float(m.get("liquidityNum") or m.get("liquidity")),
                    one_day_change=_to_float(m.get("oneDayPriceChange")),
                    best_bid=_to_float_or_none(m.get("bestBid")),
                    best_ask=_to_float_or_none(m.get("bestAsk")),
                    last_trade=_to_float_or_none(m.get("lastTradePrice")),
                    description=str(m.get("description") or ""),
                    category=_extract_category(m),
                )
            )
            if len(out) >= limit:
                break
        except Exception:
            continue

    return out
