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
    ta, tb = _tokens(a), _tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)          # Jaccard


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
    candidates: List[MatchCandidate] = []
    for a in venue_a:
        da = _close_date(a.close_time)
        for b in venue_b:
            sim = _similarity(a.event_title, b.event_title)
            if sim < min_similarity:
                continue
            db = _close_date(b.close_time)
            if da and db and abs((da - db).days) > max_close_gap_days:
                continue
            gap = None
            if a.implied_prob is not None and b.implied_prob is not None:
                gap = abs(a.implied_prob - b.implied_prob) * 100.0
            candidates.append(MatchCandidate(a=a, b=b, title_similarity=sim, gap_pp=gap))

    candidates.sort(key=lambda c: c.title_similarity, reverse=True)
    return candidates
