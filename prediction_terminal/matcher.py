"""Candidate event matcher.

This is deliberately a CRUDE first-pass filter — token overlap + a date guard — NOT
the judgment layer. Its only job is to narrow thousands of markets to a handful of
plausible same-event pairs. The real "is this actually the same question?" decision is
Step 1 of the master prompt (the LLM identity gate), because token overlap cannot tell
"Fed holds in July" from "Fed holds in September". Keep this cheap; keep the judgment in the prompt.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import List

from models import NormalizedMarket, MatchCandidate

_STOP = {
    "will", "the", "a", "an", "be", "to", "of", "in", "on", "at", "for", "and",
    "or", "is", "are", "by", "this", "that", "with", "than", "over", "under",
    "yes", "no", "market", "resolve", "during", "before", "after",
}


def _tokens(title: str) -> set:
    words = re.findall(r"[a-z0-9]+", title.lower())
    return {w for w in words if w not in _STOP and len(w) > 1}


def _similarity(a: str, b: str) -> float:
    """Jaccard over title tokens. Kept for callers/tests that pass raw strings;
    the match() hot loop uses pre-tokenized sets instead (see _jaccard)."""
    ta, tb = _tokens(a), _tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def _jaccard(ta: set, tb: set, min_similarity: float) -> float:
    """Jaccard on already-tokenized sets, with a cheap size prune.

    |ta & tb| <= min(|ta|,|tb|) and |ta | tb| >= max(|ta|,|tb|), so similarity can
    never exceed min/max. When that ceiling is already below the threshold we can
    reject the pair without building either set operation — which is most pairs.
    """
    if not ta or not tb:
        return 0.0
    la, lb = len(ta), len(tb)
    if (la if la < lb else lb) < min_similarity * (la if la > lb else lb):
        return 0.0
    inter = len(ta & tb)
    if not inter:
        return 0.0
    return inter / (la + lb - inter)           # |a|+|b|-|a&b| == |a|b| , no second set built


def _close_date(iso: str):
    try:
        return datetime.fromisoformat(iso.replace("Z", "+00:00")).date()
    except (ValueError, AttributeError):
        return None


def match(
    venue_a: List[NormalizedMarket],
    venue_b: List[NormalizedMarket],
    min_similarity: float = 0.30,
    max_close_gap_days: int = 3,
) -> List[MatchCandidate]:
    """Return candidate cross-venue pairs, best title-similarity first.

    Date guard: if both close_times parse, drop pairs closing more than
    `max_close_gap_days` apart (a cheap way to separate same-topic-different-date events).
    """
    # Tokenize and date-parse ONCE per market instead of once per pair. The naive
    # form re-tokenized both titles inside the inner loop, so an 83x50 fetch did
    # ~8k tokenizations and ~8k date parses to evaluate 4k pairs; this does 133.
    toks_b = [_tokens(b.event_title) for b in venue_b]
    dates_b = [_close_date(b.close_time) for b in venue_b]

    candidates: List[MatchCandidate] = []
    for a in venue_a:
        ta = _tokens(a.event_title)
        if not ta:
            continue
        da = _close_date(a.close_time)
        for b, tb, db in zip(venue_b, toks_b, dates_b):
            # Date guard first — an integer compare is far cheaper than set math,
            # and it rejects same-topic-different-meeting pairs (the July-vs-September
            # case) before we ever score them.
            if da and db and abs((da - db).days) > max_close_gap_days:
                continue
            sim = _jaccard(ta, tb, min_similarity)
            if sim < min_similarity:
                continue
            gap = None
            if a.implied_prob is not None and b.implied_prob is not None:
                gap = abs(a.implied_prob - b.implied_prob) * 100.0
            candidates.append(MatchCandidate(a=a, b=b, title_similarity=sim, gap_pp=gap))

    candidates.sort(key=lambda c: c.title_similarity, reverse=True)
    return candidates
