"""Devig — strip bookmaker vig from a multi-way market to recover fair probabilities.

A book's quoted implied probabilities sum to MORE than 1; the excess is the vig (a.k.a.
overround / juice). To compare a sportsbook line against a Kalshi price we need the book's
FAIR probability — what it implies before its margin.

v0 uses the MULTIPLICATIVE method only: renormalize so the sides sum to 1, keeping each
side's share of the total constant.

    fair_p_i = book_p_i / Σ_j book_p_j

This assumes the vig is spread proportionally across outcomes. It is the standard baseline;
favorite-longshot-aware methods (Shin, power) are deliberately out of scope for v0.

Pure functions, no I/O, no dependencies — every branch is unit-tested.
"""

from __future__ import annotations

from typing import List, Sequence, Tuple


def overround(probs: Sequence[float]) -> float:
    """The book's margin: Σ book_p − 1. ~0.04 for a typical two-way NFL line; a clean
    (already-fair) market returns ~0.0. Negative would imply an arb and is surfaced, not
    hidden."""
    _validate(probs)
    return sum(probs) - 1.0


def devig_multiplicative(probs: Sequence[float]) -> List[float]:
    """Multiplicative devig: renormalize `probs` to sum to 1, preserving ratios.

    Input: each book-implied prob, vig included, in (0, 1]. Output: fair probs summing to 1.
    Order is preserved, so the caller keeps its side↔value mapping.
    """
    _validate(probs)
    total = sum(probs)
    return [p / total for p in probs]


def fair_pair(p_a: float, p_b: float) -> Tuple[float, float]:
    """Two-sided convenience (over/under or home/away). Returns (fair_a, fair_b)."""
    fa, fb = devig_multiplicative([p_a, p_b])
    return fa, fb


def _validate(probs: Sequence[float]) -> None:
    if len(probs) < 2:
        raise ValueError("devig needs at least two sides of a market")
    for p in probs:
        if p is None:
            raise ValueError("cannot devig a None probability")
        if not (0.0 < p <= 1.0):
            raise ValueError(f"implied prob out of range (0,1]: {p!r}")
    if sum(probs) <= 0.0:
        raise ValueError("implied probabilities sum to <= 0")
