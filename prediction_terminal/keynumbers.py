"""NFL key-number push mass — quantify the structural gap the wedge trades on.

WHY THIS EXISTS
---------------
The identity gate can tell that a Kalshi spread contract and a sportsbook spread line
settle differently on part of the margin axis (SUBTLY_DIFFERENT). What it does NOT tell you
is HOW MUCH that difference is worth. A pair that disagrees only when the game lands on
margin 3 (the single most common NFL result) is a real structural edge; a pair that
disagrees only on margin 17 is noise. Both are SUBTLY_DIFFERENT to the gate.

This module supplies the missing scalar: the probability mass sitting on the integer
margins where the two contracts disagree. That is the wedge — and it is LATENCY-IMMUNE,
because it turns on contract structure (which margins are disputed) and a stable historical
distribution, not on a live price. A 10-minute-delayed book line does not corrupt it.

THE DISTRIBUTION
----------------
`_MARGIN_PMF` is a STATIC empirical prior: approximate frequencies of NFL final margins of
victory (absolute value, regulation + OT), from widely-published historical betting data.
It is deliberately a fixed table, not a live model:
  - It ranks and sizes key-number mismatches; it is NOT a settlement-grade probability.
  - Key numbers (3, 7, 6, 10, 14) carry the mass that makes the wedge real; the exact
    second-decimal is not load-bearing for ranking.
  - A production version should refit these from a rolling window of results. Until then
    this is honestly a prior, and callers should treat the output as "how big, roughly"
    not "the true edge in cents".

Margins not in the table fall back to a small tail value. Pure functions, no I/O.
"""

from __future__ import annotations

import math
from typing import List, Tuple

INF = float("inf")
Interval = Tuple[float, float]

# Approximate historical NFL final-margin-of-victory frequencies (|margin|, reg + OT).
# Static prior — see module docstring. Key numbers 3/7/6/10/14 carry the decisive mass.
_MARGIN_PMF = {
    1: 0.023, 2: 0.033, 3: 0.095, 4: 0.052, 5: 0.030,
    6: 0.058, 7: 0.073, 8: 0.036, 9: 0.019, 10: 0.056,
    11: 0.030, 12: 0.015, 13: 0.032, 14: 0.041, 15: 0.012,
    16: 0.021, 17: 0.028, 18: 0.011, 19: 0.010, 20: 0.017,
    21: 0.015,
}
# Every larger (or zero-tie) margin, lumped: one bucket over ~28% of the tail. Per-margin
# it is tiny, which is exactly why non-key-number disagreements score as noise.
_TAIL_PER_MARGIN = 0.004


def margin_prob(margin: float) -> float:
    """P(final margin of victory == |margin|) under the static prior."""
    return _MARGIN_PMF.get(int(abs(margin)), _TAIL_PER_MARGIN)


def hinge_margin(leg: Interval):
    """The nearest LOSING integer margin for an open-ended spread leg — the 'heartbreak'
    number the contract turns on. For a win-region (lo, inf) it is lo-1; for (-inf, hi) it
    is hi+1. Returns None for bounded or total legs (nothing single-margin to hinge on).

    This drives the always-on push-risk literacy: even when a contract carries no exploitable
    edge, the user should know which exact result flips it and how common that result is.
    """
    lo, hi = leg
    if hi == INF and lo != -INF:
        return int(lo) - 1
    if lo == -INF and hi != INF:
        return int(hi) + 1
    return None


def disputed_margins(a: Interval, b: Interval, cap: int = 60) -> List[int]:
    """Integer margins on which membership in `a` and `b` differs (their symmetric
    difference on the integer axis).

    Both intervals are integer-snapped margin legs from identity.py, so an endpoint that is
    a finite float is the smallest/largest INCLUDED integer. Two genuinely-subtle legs share
    the same infinite tail, so their symmetric difference is a finite set near the disputed
    boundary. `cap` bounds the scan defensively; a symmetric difference that would exceed it
    (e.g. two disjoint bounded legs) is not the wedge's case and returns what fits.
    """
    lo = max(min(_finite_lo(a), _finite_lo(b)), -cap)
    hi = min(max(_finite_hi(a), _finite_hi(b)), cap)
    out = []
    for m in range(int(math.floor(lo)), int(math.ceil(hi)) + 1):
        if _contains(a, m) != _contains(b, m):
            out.append(m)
    return out


def push_mass(a: Interval, b: Interval) -> Tuple[float, List[int]]:
    """(probability mass on the disputed margins, the disputed margins).

    This is the wedge's headline number: how much of the outcome distribution falls exactly
    where the Kalshi contract and the book line pay out differently. Higher = more real.
    """
    margins = disputed_margins(a, b)
    return sum(margin_prob(m) for m in margins), margins


def _contains(iv: Interval, m: int) -> bool:
    return iv[0] <= m <= iv[1]


def _finite_lo(iv: Interval) -> float:
    return iv[0] if iv[0] != -INF else iv[1]


def _finite_hi(iv: Interval) -> float:
    return iv[1] if iv[1] != INF else iv[0]
