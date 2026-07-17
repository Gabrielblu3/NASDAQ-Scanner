"""Shared normalized schema. Every venue adapter emits NormalizedMarket so the
matcher and the master prompt never see venue-specific quirks (Polymarket prices
are 0-1 probs; Kalshi prices are integer cents — each adapter absorbs its own units)."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class NormalizedMarket:
    venue: str                       # "polymarket" | "kalshi"
    market_id: str                   # venue-native id/ticker
    event_title: str                 # human-readable question
    outcome: str                     # for binary markets, the "Yes" side
    implied_prob: Optional[float]    # 0.0-1.0, or None if unpriced/illiquid
    resolution_criteria: str         # full resolution text (drives the Step-1 identity gate)
    settlement_source: str           # best-effort extracted source of truth
    close_time: str                  # ISO8601
    volume_usd: Optional[float] = None
    liquidity_usd: Optional[float] = None
    raw: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = asdict(self)
        d.pop("raw", None)           # keep prompt payload lean
        return d


@dataclass
class MatchCandidate:
    a: NormalizedMarket              # market from venue A
    b: NormalizedMarket              # market from venue B
    title_similarity: float          # 0.0-1.0 token overlap
    gap_pp: Optional[float]          # |prob_a - prob_b| in percentage points, None if either unpriced

    def to_dict(self) -> dict:
        return {
            "title_similarity": round(self.title_similarity, 3),
            "gap_pp": None if self.gap_pp is None else round(self.gap_pp, 1),
            "a": self.a.to_dict(),
            "b": self.b.to_dict(),
        }
