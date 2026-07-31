"""Event identity gate — Step 1 of the master prompt, enforced deterministically.

WHY THIS IS CODE AND NOT A PROMPT
---------------------------------
The matcher scores titles by token overlap, which cannot tell a *disagreement* from a
*complement*. Live example, 2026-07-30: Polymarket "no change in Fed interest rates after
the September 2026 meeting" (44.5%) matched all five Kalshi September legs at identical
title similarity 0.31, so the top-ranked candidate was a 42.0pp "gap" against "Hike rates
by >25bps" (2.5%). Those two contracts do not disagree — they cannot both pay out. The
real pair, "no change" vs "Hike by 0bps" (43.0%), is a 1.5pp gap ranked last.

A gap is only meaningful when both legs pay out in the SAME world-state. That is a
structural fact about the contracts, not a judgement call, so it belongs in code where it
is testable and free. The LLM keeps the genuinely hard reasoning (is this liquidity or a
real view, has it decayed, is it capturable); it should never be asked to re-derive
arithmetic we can settle exactly.

THE MODEL
---------
Every rate-decision contract is a claim about one number: the change in the upper bound of
the target federal funds range, in basis points, at one specific FOMC meeting. So a leg is
an INTERVAL on that axis:

    "no change" / "0bps"        ->  [0, 0]
    "hike by 25bps"             ->  [25, 25]
    "hike by >25bps"            ->  [26, +inf)
    "increase by 50+ bps"       ->  [50, +inf)
    "cut by 25bps"              ->  [-25, -25]
    "decrease by 50+ bps"       ->  (-inf, -50]

Two legs are the same question only if their intervals are identical. Disjoint intervals
are complements — never a gap. Overlapping-but-unequal intervals (Kalshi ">25bps" vs
Polymarket "50+ bps" — the 26-49bps sliver differs) are SUBTLY_DIFFERENT: close enough to
look tradeable, different enough to settle opposite. That sliver is precisely the kind of
resolution nuance that makes a gap look like free money and is not.

FAIL-CLOSED
-----------
Anything we cannot parse into (family, referent, leg, authority) is NOT SAME_QUESTION.
Silence is a rejection. A missed real pair costs us one candidate; a fake pair shown to a
trader as edge costs us the trader.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Tuple

from models import NormalizedMarket

# --- families -------------------------------------------------------------------------
# A "change" market prices the size of the move at one meeting. A "level" market prices
# where the rate ENDS UP. Relating the two requires knowing the current rate and the exact
# rounding convention, so we refuse to cross them rather than guess.
FAMILY_CHANGE = "fed_rate_change"
FAMILY_LEVEL = "fed_rate_level"
FAMILY_UNKNOWN = "unknown"

SAME_QUESTION = "SAME_QUESTION"
SUBTLY_DIFFERENT = "SUBTLY_DIFFERENT"
DIFFERENT_QUESTION = "DIFFERENT_QUESTION"

_MONTHS = {m: i for i, m in enumerate(
    ["january", "february", "march", "april", "may", "june", "july",
     "august", "september", "october", "november", "december"], start=1)}
_MONTH_ABBR = {m[:3]: i for m, i in _MONTHS.items()}

_HIKE_WORDS = ("hike", "increase", "raise", "raises", "hikes", "increases")
_CUT_WORDS = ("cut", "decrease", "lower", "reduce", "cuts", "decreases")
_HOLD_WORDS = ("no change", "unchanged", "hold rates", "holds rates", "leave rates")

INF = float("inf")
Interval = Tuple[float, float]


@dataclass(frozen=True)
class EventIdentity:
    family: str
    referent: Optional[str]        # canonical meeting key, e.g. "2026-09"
    leg: Optional[Interval]        # bps-change interval, or None for level markets
    level_bound: Optional[float]   # for level markets: the threshold in percent
    authority: Optional[str]       # canonical settlement authority
    close_date: Optional[str]      # ISO date

    def describe(self) -> str:
        if self.family == FAMILY_LEVEL:
            return f"level>{self.level_bound}% @ {self.referent}"
        if self.leg is None:
            return f"unparsed @ {self.referent}"
        return f"{_leg_label(self.leg)} @ {self.referent}"


@dataclass(frozen=True)
class IdentityVerdict:
    status: str                    # SAME_QUESTION | SUBTLY_DIFFERENT | DIFFERENT_QUESTION
    failed_check: Optional[str]    # referent | outcome_leg | authority | close | family
    reason: str                    # human-readable, quotes the offending values

    @property
    def is_same(self) -> bool:
        return self.status == SAME_QUESTION


def _leg_label(iv: Interval) -> str:
    lo, hi = iv
    if lo == 0 and hi == 0:
        return "hold(0bps)"
    if lo == hi:
        return f"{'hike' if lo > 0 else 'cut'} {abs(lo):.0f}bps"
    if hi == INF:
        return f"hike >={lo:.0f}bps"
    if lo == -INF:
        return f"cut >={abs(hi):.0f}bps"
    return f"[{lo},{hi}]bps"


# --- extraction -----------------------------------------------------------------------

def _parse_meeting(text: str) -> Optional[str]:
    """Canonical meeting key 'YYYY-MM' from '... September 2026 meeting ...'."""
    t = text.lower()
    m = re.search(r"\b([a-z]{3,9})\s+(\d{4})\b", t)
    if m:
        month = _MONTHS.get(m.group(1)) or _MONTH_ABBR.get(m.group(1)[:3])
        if month:
            return f"{int(m.group(2))}-{month:02d}"
    # Kalshi ticker form: KXFEDDECISION-26SEP-H0
    m = re.search(r"-(\d{2})([a-z]{3})-", text.lower())
    if m:
        month = _MONTH_ABBR.get(m.group(2))
        if month:
            return f"20{m.group(1)}-{month:02d}"
    return None


def _parse_leg(text: str) -> Optional[Interval]:
    """Map an outcome description onto a bps-change interval. None if unparseable."""
    t = text.lower()

    if any(w in t for w in _HOLD_WORDS):
        return (0.0, 0.0)

    # magnitude + open-endedness. ">25bps", "50+ bps", "25 bps"
    m = re.search(r"(>|at least|more than|over)?\s*(\d+)\s*(\+)?\s*bps", t)
    if not m:
        return None
    open_above = bool(m.group(1)) or bool(m.group(3))
    mag = float(m.group(2))

    # "Hike rates by 0bps" is Kalshi's spelling of hold — magnitude wins over direction.
    if mag == 0 and not open_above:
        return (0.0, 0.0)

    hike = any(w in t for w in _HIKE_WORDS)
    cut = any(w in t for w in _CUT_WORDS)
    if hike == cut:                      # neither, or ambiguously both
        return None

    if hike:
        # ">25bps" excludes 25 itself; "50+ bps" includes 50.
        lo = mag + 1 if m.group(1) else mag
        return (lo, INF) if open_above else (mag, mag)
    lo_neg = -(mag + 1) if m.group(1) else -mag
    return (-INF, lo_neg) if open_above else (-mag, -mag)


def _parse_level(text: str) -> Optional[float]:
    """Threshold for 'upper bound ... above X%' style level markets."""
    t = text.lower()
    if "upper bound" not in t and "federal funds rate" not in t:
        return None
    m = re.search(r"(?:above|below|at least|under)\s+([\d.]+)\s*%", t)
    return float(m.group(1)) if m else None


def _parse_authority(text: str) -> Optional[str]:
    t = text.lower()
    if "fomc" in t or "federal open market committee" in t or "federal reserve" in t or "fed " in t:
        return "federal_reserve_fomc"
    return None


def _close_date(iso: str) -> Optional[str]:
    try:
        return datetime.fromisoformat(iso.replace("Z", "+00:00")).date().isoformat()
    except (ValueError, AttributeError):
        return None


def extract(m: NormalizedMarket) -> EventIdentity:
    """Structured identity for one market.

    The outcome leg comes from the TITLE, never from the resolution text. Within a series
    every market shares the same resolution boilerplate — Polymarket's Fed contracts all
    end "...will resolve to the 'No change' bracket", so reading the leg out of the blob
    made every leg parse as hold(0bps) and killed the real pairs. The title is the only
    field that distinguishes legs within a series. Resolution text is a fallback for the
    rare title that carries no magnitude at all.

    Referent and authority DO read the whole blob: those are consistent across a series by
    construction, and the ticker/resolution often carry them when the title does not.
    """
    blob = " ".join(filter(None, (m.event_title, m.resolution_criteria, m.market_id)))
    title = m.event_title or ""

    leg = _parse_leg(title)
    level = _parse_level(title)
    if leg is None and level is None:
        leg = _parse_leg(m.resolution_criteria or "")
        level = _parse_level(m.resolution_criteria or "")

    # A level threshold only wins when there is no change-leg reading, so that
    # "no change ... defined by the upper bound" (Polymarket's boilerplate) stays a
    # change market rather than being misread as a level market.
    if leg is None and level is not None:
        family = FAMILY_LEVEL
    elif leg is not None:
        family = FAMILY_CHANGE
        level = None
    else:
        family = FAMILY_UNKNOWN

    return EventIdentity(
        family=family,
        referent=_parse_meeting(blob),
        leg=leg,
        level_bound=level,
        authority=_parse_authority(blob),
        close_date=_close_date(m.close_time),
    )


# --- the gate -------------------------------------------------------------------------

def _overlaps(x: Interval, y: Interval) -> bool:
    return x[0] <= y[1] and y[0] <= x[1]


def check(a: NormalizedMarket, b: NormalizedMarket,
          max_close_gap_days: int = 1) -> IdentityVerdict:
    """The four-part gate on two markets. Extracts, then compares."""
    return compare(extract(a), extract(b), max_close_gap_days)


def compare(ia: EventIdentity, ib: EventIdentity,
            max_close_gap_days: int = 1) -> IdentityVerdict:
    """The four-part gate on two already-extracted identities.

    Split out from check() so callers scanning many pairs extract once per market rather
    than twice per pair — the same O(n+m) vs O(n*m) difference that dominates the matcher.
    """

    # 0. Family — never cross a "how big is the move" market with a "where does it end up"
    #    market. Relating them needs the current rate and a rounding convention.
    if ia.family == FAMILY_UNKNOWN or ib.family == FAMILY_UNKNOWN:
        return IdentityVerdict(DIFFERENT_QUESTION, "family",
                               f"unparseable contract structure ({ia.family} vs {ib.family}) — "
                               f"fail-closed")
    if ia.family != ib.family:
        return IdentityVerdict(DIFFERENT_QUESTION, "family",
                               f"{ia.family} vs {ib.family}: a rate-change market and a "
                               f"rate-level market are not the same question")

    # 1. Referent — same meeting.
    if ia.referent is None or ib.referent is None:
        return IdentityVerdict(DIFFERENT_QUESTION, "referent",
                               "could not resolve which meeting one side refers to — fail-closed")
    if ia.referent != ib.referent:
        return IdentityVerdict(DIFFERENT_QUESTION, "referent",
                               f"different meetings: {ia.referent} vs {ib.referent}")

    # 2. Outcome leg — the check that catches complements.
    if ia.family == FAMILY_CHANGE:
        if ia.leg is None or ib.leg is None:
            return IdentityVerdict(DIFFERENT_QUESTION, "outcome_leg",
                                   "could not resolve an outcome leg — fail-closed")
        if not _overlaps(ia.leg, ib.leg):
            return IdentityVerdict(
                DIFFERENT_QUESTION, "outcome_leg",
                f"complementary legs: {_leg_label(ia.leg)} vs {_leg_label(ib.leg)} cannot both "
                f"pay out, so the price difference is not a disagreement")
        if ia.leg != ib.leg:
            return IdentityVerdict(
                SUBTLY_DIFFERENT, "outcome_leg",
                f"overlapping but unequal legs: {_leg_label(ia.leg)} vs {_leg_label(ib.leg)} — "
                f"they settle differently in part of the range")
    elif ia.level_bound != ib.level_bound:
        return IdentityVerdict(DIFFERENT_QUESTION, "outcome_leg",
                               f"different thresholds: {ia.level_bound}% vs {ib.level_bound}%")

    # 3. Authority — same settlement source of truth.
    if ia.authority is None or ib.authority is None:
        return IdentityVerdict(DIFFERENT_QUESTION, "authority",
                               "could not confirm a shared settlement authority — fail-closed")
    if ia.authority != ib.authority:
        return IdentityVerdict(DIFFERENT_QUESTION, "authority",
                               f"different settlement authority: {ia.authority} vs {ib.authority}")

    # 4. Close — same resolution window.
    if ia.close_date is None or ib.close_date is None:
        return IdentityVerdict(DIFFERENT_QUESTION, "close",
                               "missing close date on one side — fail-closed")
    da = datetime.fromisoformat(ia.close_date).date()
    db = datetime.fromisoformat(ib.close_date).date()
    if abs((da - db).days) > max_close_gap_days:
        return IdentityVerdict(DIFFERENT_QUESTION, "close",
                               f"close dates {ia.close_date} vs {ib.close_date} differ by more "
                               f"than {max_close_gap_days}d")

    return IdentityVerdict(SAME_QUESTION, None,
                           f"same meeting ({ia.referent}), same leg ({_leg_label(ia.leg)}), "
                           f"same authority, closes within {max_close_gap_days}d"
                           if ia.leg else f"same meeting ({ia.referent}), same threshold")


def pair_markets(venue_a, venue_b, max_close_gap_days: int = 1):
    """Join two venues on structured identity. Returns (same, subtle) pair lists.

    This replaces title-similarity as the way pairs are FOUND, rather than only judging
    pairs that similarity happened to surface. Token overlap was always a proxy for "same
    event"; once identity is structured we can index on it exactly.

    Measured on the live Fed corpus (2026-07-30, 68 x 147 markets): the similarity filter
    at its 0.30 threshold surfaced 1 of the 3 true pairs — the other two scored 0.29 and
    were dropped, purely because Polymarket writes "increase interest rates by 25 bps" and
    Kalshi writes "Hike rates by 25bps". Wording differences are not evidence about the
    contract. Indexing on (family, referent, leg, authority) finds all three.

    Cost is O(n + m) extractions plus a dict lookup per market, versus O(n*m) extractions
    for the scan-every-pair form (892ms -> single-digit ms on that corpus).
    """
    ids_a = [(m, extract(m)) for m in venue_a]
    ids_b = [(m, extract(m)) for m in venue_b]

    # Exact index for the SAME_QUESTION join.
    index: dict = {}
    for m, i in ids_b:
        if i.family == FAMILY_UNKNOWN or i.referent is None or i.authority is None:
            continue                      # fail-closed: unindexable is unmatchable
        index.setdefault((i.family, i.referent, i.leg, i.level_bound, i.authority), []).append((m, i))

    # Meeting-level buckets for the SUBTLY_DIFFERENT sweep, which needs leg *overlap*
    # rather than leg equality and so cannot be answered by an exact key.
    by_meeting: dict = {}
    for m, i in ids_b:
        if i.family == FAMILY_CHANGE and i.referent and i.leg:
            by_meeting.setdefault(i.referent, []).append((m, i))

    same, subtle = [], []
    for a, ia in ids_a:
        if ia.family == FAMILY_UNKNOWN or ia.referent is None or ia.authority is None:
            continue
        key = (ia.family, ia.referent, ia.leg, ia.level_bound, ia.authority)
        for b, ib in index.get(key, ()):
            v = compare(ia, ib, max_close_gap_days)
            if v.is_same:
                same.append((a, b, v))

        if ia.family == FAMILY_CHANGE and ia.leg:
            for b, ib in by_meeting.get(ia.referent, ()):
                if ib.leg == ia.leg:
                    continue              # already handled by the exact join
                v = compare(ia, ib, max_close_gap_days)
                if v.status == SUBTLY_DIFFERENT:
                    subtle.append((a, b, v))

    return same, subtle
