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

import math
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

# NFL families. Same interval machinery as the Fed change-market, on a different axis:
#   nfl_total  -> total points scored in one game       ("over 45.5" -> (45.5, +inf))
#   nfl_spread -> game margin, from a canonical team's perspective (see _spread_interval)
# The referent is the game (a canonical unordered team-pair), and settlement authority is
# the game result itself, so both venues share one authority constant.
FAMILY_NFL_TOTAL = "nfl_total"
FAMILY_NFL_SPREAD = "nfl_spread"
AUTHORITY_NFL = "nfl_game_result"

# Families whose identity turns on an interval `leg` (vs the level market's scalar bound).
_LEG_FAMILIES = (FAMILY_CHANGE, FAMILY_NFL_TOTAL, FAMILY_NFL_SPREAD)

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
    # The WIN-OR-PUSH interval: margins on which the contract does NOT lose money (win OR
    # refund). For a binary Kalshi contract it equals `leg` (a binary market can never push).
    # For a sportsbook line at an INTEGER handicap/total it is `leg` widened by the one margin
    # that lands exactly on the number and refunds. Two contracts can share an identical win
    # `leg` yet differ here — that is the push hiding inside a look-alike line.
    push_leg: Optional[Interval] = None

    def describe(self) -> str:
        if self.family == FAMILY_LEVEL:
            return f"level>{self.level_bound}% @ {self.referent}"
        if self.leg is None:
            return f"unparsed @ {self.referent}"
        return f"{_leg_label(self.leg, self.family)} @ {self.referent}"


@dataclass(frozen=True)
class IdentityVerdict:
    status: str                    # SAME_QUESTION | SUBTLY_DIFFERENT | DIFFERENT_QUESTION
    failed_check: Optional[str]    # referent | outcome_leg | authority | close | family
    reason: str                    # human-readable, quotes the offending values

    @property
    def is_same(self) -> bool:
        return self.status == SAME_QUESTION


def _leg_label(iv: Interval, family: str = FAMILY_CHANGE) -> str:
    lo, hi = iv
    if family == FAMILY_NFL_TOTAL:
        if hi == INF:
            return f"over {lo:g}"
        if lo == -INF:
            return f"under {hi:g}"
        return f"[{lo:g},{hi:g}]pts"
    if family == FAMILY_NFL_SPREAD:
        if hi == INF:
            return f"margin>{lo:g}"
        if lo == -INF:
            return f"margin<{hi:g}"
        return f"[{lo:g},{hi:g}]margin"
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


# --- NFL extraction -------------------------------------------------------------------
# Canonical team codes. Both venues must derive the SAME game key, so we normalize every
# spelling a market might use (nickname, "City Nickname", the code itself) to one code.
# Bare ambiguous cities ("los angeles", "new york") are intentionally NOT keys — they
# cannot disambiguate the two co-located franchises, so we require the nickname.
_NFL_TEAMS = {
    "bills": "BUF", "buffalo bills": "BUF",
    "dolphins": "MIA", "miami dolphins": "MIA",
    "patriots": "NE", "new england patriots": "NE",
    "jets": "NYJ", "new york jets": "NYJ",
    "ravens": "BAL", "baltimore ravens": "BAL",
    "bengals": "CIN", "cincinnati bengals": "CIN",
    "browns": "CLE", "cleveland browns": "CLE",
    "steelers": "PIT", "pittsburgh steelers": "PIT",
    "texans": "HOU", "houston texans": "HOU",
    "colts": "IND", "indianapolis colts": "IND",
    "jaguars": "JAX", "jacksonville jaguars": "JAX",
    "titans": "TEN", "tennessee titans": "TEN",
    "broncos": "DEN", "denver broncos": "DEN",
    "chiefs": "KC", "kansas city chiefs": "KC", "kansas city": "KC",
    "raiders": "LV", "las vegas raiders": "LV",
    "chargers": "LAC", "los angeles chargers": "LAC",
    "cowboys": "DAL", "dallas cowboys": "DAL",
    "giants": "NYG", "new york giants": "NYG",
    "eagles": "PHI", "philadelphia eagles": "PHI",
    "commanders": "WAS", "washington commanders": "WAS",
    "bears": "CHI", "chicago bears": "CHI",
    "lions": "DET", "detroit lions": "DET",
    "packers": "GB", "green bay packers": "GB", "green bay": "GB",
    "vikings": "MIN", "minnesota vikings": "MIN",
    "falcons": "ATL", "atlanta falcons": "ATL",
    "panthers": "CAR", "carolina panthers": "CAR",
    "saints": "NO", "new orleans saints": "NO",
    "buccaneers": "TB", "bucs": "TB", "tampa bay buccaneers": "TB", "tampa bay": "TB",
    "cardinals": "ARI", "arizona cardinals": "ARI",
    "rams": "LA", "los angeles rams": "LA",
    "49ers": "SF", "niners": "SF", "san francisco 49ers": "SF", "san francisco": "SF",
    "seahawks": "SEA", "seattle seahawks": "SEA",
}
# Longest aliases first so "kansas city chiefs" wins over "kansas city".
_NFL_ALIASES = sorted(_NFL_TEAMS, key=len, reverse=True)

# Over/under wording, split by boundary. NFL points & margins are integers, so we snap
# every line to an integer-endpoint interval: strict "over 45.5" -> [46, inf); inclusive
# "46 or more" -> [46, inf). Snapping is what makes over/under exact complements (they no
# longer share the .5 point) while still flagging a 45.5-vs-46 line move as SUBTLY_DIFFERENT.
_OVER_EXCL = ("over", "more than", "greater than", "above")
_OVER_INCL = ("at least", "or more")
_UNDER_EXCL = ("under", "less than", "fewer than", "below")
_UNDER_INCL = ("or fewer", "or less", "at most")
# A total is the COMBINED game score; require an explicit combined-scoring cue so a
# single-team team-total ("Chiefs over 30.5") is not mistaken for the game total.
_TOTAL_CUES = ("combined", "combine", "total points", "total of", "game total",
               "points scored", "total score")
_SPREAD_CUES = ("win by", "beat", "margin", "cover", "spread", "by more than",
                "by at least", "by over")


def _nfl_team_codes(text: str) -> list:
    """Distinct canonical codes named in `text`, in first-appearance order."""
    t = (text or "").lower()
    hits = []
    for alias in _NFL_ALIASES:
        if re.search(rf"\b{re.escape(alias)}\b", t):
            code = _NFL_TEAMS[alias]
            if code not in hits:
                hits.append((t.index(alias), code))
    return [c for _, c in sorted(hits)]


def _nfl_referent(codes) -> Optional[str]:
    """Order-independent game key from exactly two team codes. The date is NOT baked in
    (a late game crossing UTC midnight would desync it); the close-date gate separates the
    once- or twice-a-season repeat meetings between the same teams instead."""
    uniq = sorted(set(codes))
    return "-".join(uniq) if len(uniq) == 2 else None


_NUM_RE = re.compile(r"\d+(?:\.\d+)?")


def _nfl_line_number(text: str, pre_cues, post_cues=()) -> Optional[float]:
    """The betting line, read as the number ADJACENT to the scoring/spread cue it attaches to,
    not the first number in the blob. Masking team names stopped a digit inside "49ers" from
    being read as the line, but that fixed one instance of a class: any digit ahead of the line
    — a week number ("Week 2"), a date ("Sep 14"), a ticker fragment — would still win a
    first-number scan and hand back a WRONG leg, the one failure mode the gate is built to never
    have.

    Direction matters: most cues precede their number ("over 45.5", "by more than 3.5"), while
    "or more"/"or fewer" follow it ("46 or more"). Reading the FIRST number after a pre-cue and
    the LAST number before a post-cue means a stray date sitting just before an unrelated cue
    (e.g. "Sep 14 beat ...") is never a candidate — it is not on the number-bearing side of any
    cue. Among candidates the one with the smallest cue-to-number gap wins. Fail closed (None)
    when no cue has a number on its expected side."""
    t = (text or "").lower()
    for alias in _NFL_ALIASES:
        t = re.sub(rf"\b{re.escape(alias)}\b", " ", t)
    cands = []  # (gap, value)
    for cue in pre_cues:
        i = t.find(cue)
        if i == -1:
            continue
        mm = _NUM_RE.search(t, i + len(cue))
        if mm:
            cands.append((mm.start() - (i + len(cue)), float(mm.group())))
    for cue in post_cues:
        i = t.find(cue)
        if i == -1:
            continue
        before = list(_NUM_RE.finditer(t, 0, i))
        if before:
            mm = before[-1]
            cands.append((i - mm.end(), float(mm.group())))
    if not cands:
        return None
    return min(cands, key=lambda gv: gv[0])[1]


_TOTAL_PRE_CUES = _OVER_EXCL + ("at least",) + _UNDER_EXCL + ("at most",)
_TOTAL_POST_CUES = ("or more", "or fewer", "or less")
_SPREAD_PRE_CUES = _SPREAD_CUES + ("by", "+")


def _gt_interval(x: float, inclusive: bool) -> Interval:
    """Integer-snapped 'score greater than x' ( >= x if inclusive )."""
    lo = math.ceil(x) if inclusive else math.floor(x) + 1
    return (float(lo), INF)


def _lt_interval(x: float, inclusive: bool) -> Interval:
    """Integer-snapped 'score less than x' ( <= x if inclusive )."""
    hi = math.floor(x) if inclusive else math.ceil(x) - 1
    return (-INF, float(hi))


def _nfl_total_interval(text: str) -> Optional[Interval]:
    """Combined-total wording -> integer-snapped points interval, or None if unreadable."""
    t = (text or "").lower()
    line = _nfl_line_number(t, _TOTAL_PRE_CUES, _TOTAL_POST_CUES)
    if line is None:
        return None
    over_excl, over_incl = _any(t, _OVER_EXCL), _any(t, _OVER_INCL)
    under_excl, under_incl = _any(t, _UNDER_EXCL), _any(t, _UNDER_INCL)
    is_over, is_under = over_excl or over_incl, under_excl or under_incl
    if is_over == is_under:              # neither, or contradictory
        return None
    if is_over:
        return _gt_interval(line, inclusive=over_incl and not over_excl)
    return _lt_interval(line, inclusive=under_incl and not under_excl)


def _any(t: str, words) -> bool:
    return any(w in t for w in words)


def _flip(iv: Interval) -> Interval:
    """Same margin condition seen from the OTHER team: margin_T = -margin_opp."""
    lo, hi = iv
    return (-hi, -lo)


def _to_ref(iv: Interval, subject: str, ref_code: str) -> Interval:
    """Re-express a subject-team margin interval on the canonical reference team's axis, so
    both venues land on one shared axis regardless of which team they named."""
    return iv if subject == ref_code else _flip(iv)


def _spread_interval(team_code: str, handicap: float, ref_code: str) -> Interval:
    """Sportsbook side: team T at signed handicap h covers iff margin_T > -h. Integer-snapped
    (margins are whole numbers) and re-expressed on the reference axis via _to_ref."""
    return _to_ref(_gt_interval(-handicap, inclusive=False), team_code, ref_code)


def _book_push_leg(leg: Interval, line) -> Interval:
    """A sportsbook line's WIN-OR-PUSH interval. Only an INTEGER line pushes (the game can
    land exactly on it and refund); at that margin the book neither wins nor loses, so the
    win interval widens by one integer toward the boundary. A half-point line cannot push,
    so its win-or-push interval is just the win interval. Kalshi never calls this — a binary
    contract has no refund state, so its push_leg is always its leg."""
    if line is None or not float(line).is_integer():
        return leg
    lo, hi = leg
    if hi == INF and lo != -INF:
        return (lo - 1.0, INF)
    if lo == -INF and hi != INF:
        return (-INF, hi + 1.0)
    return leg


def _disputed_ints(a: Interval, b: Interval, cap: int = 60) -> list:
    """Integer margins on which membership in `a` and `b` differs — their symmetric
    difference on the integer axis. Used only to NAME the contested margin in a verdict; the
    gate's correctness turns on interval equality, not on this scan. Kept local so the gate
    stays free of the margin-frequency prior that lives in keynumbers."""
    lo = max(min(_fin_lo(a), _fin_lo(b)), -cap)
    hi = min(max(_fin_hi(a), _fin_hi(b)), cap)
    return [m for m in range(int(math.floor(lo)), int(math.ceil(hi)) + 1)
            if (a[0] <= m <= a[1]) != (b[0] <= m <= b[1])]


def _fin_lo(iv: Interval) -> float:
    return iv[0] if iv[0] != -INF else iv[1]


def _fin_hi(iv: Interval) -> float:
    return iv[1] if iv[1] != INF else iv[0]


def _nfl_spread_leg(text: str, codes, ref_code: str) -> Optional[Interval]:
    """Parse a team-subject spread to a canonical margin interval, fail-closed.

    The subject is the EARLIEST-named team (the one "win by"/"lose by" attaches to). Sign:
      favored  ('win by more than X' / '-X')   -> margin_subject >  X   (X, +inf)
      underdog ('+X')                          -> margin_subject > -X   (-X, +inf)
      losing   ('lose by more than X')         -> margin_subject < -X   (-inf, -X)
    An inclusive cue ('X or more', 'at least X', 'Xplus') keeps the endpoint (>= / <=), which
    is exactly what separates a no-push Kalshi contract from a book line where the key number
    is a live push. Without the cue the boundary is strict, matching a book '-X' cover.
    Anything else (no team in the game, no number) returns None -> DIFFERENT_QUESTION.
    """
    t = (text or "").lower()
    best = None
    for alias in _NFL_ALIASES:
        mm = re.search(rf"\b{re.escape(alias)}\b", t)
        if mm:
            code = _NFL_TEAMS[alias]
            if code in codes and (best is None or mm.start() < best[0]):
                best = (mm.start(), code)
    if best is None:
        return None
    subject = best[1]
    num = _nfl_line_number(t, _SPREAD_PRE_CUES)
    if num is None:
        return None
    plus = bool(re.search(r"\+\s*\d", t)) or "underdog" in t
    lose = "lose by" in t or "loses by" in t or "lose to" in t
    inclusive = _any(t, _OVER_INCL) or bool(re.search(r"\d\s*\+", t))
    if lose:
        subj_iv: Interval = _lt_interval(-num, inclusive=inclusive)   # margin_subject < -num
    elif plus:
        subj_iv = _gt_interval(-num, inclusive=inclusive)             # margin_subject > -num
    else:
        subj_iv = _gt_interval(num, inclusive=inclusive)              # margin_subject > num
    return _to_ref(subj_iv, subject, ref_code)


def _extract_nfl(m: NormalizedMarket) -> EventIdentity:
    """Structured identity for an NFL total/spread market (either venue).

    Sportsbook rows carry structured `raw` (market/side/line/teams) and are read from it
    directly — deterministic, no wording to parse. Everything else (Kalshi contracts) is
    parsed from the title/resolution blob and fails closed when the wording is unreadable.
    """
    raw = m.raw or {}
    if raw.get("source") == "sportsgameodds":
        away = _nfl_team_codes(raw.get("away", ""))
        home = _nfl_team_codes(raw.get("home", ""))
        codes = (away[:1] + home[:1]) or _nfl_team_codes(m.event_title)
        ref = _nfl_referent(codes)
        market, side, line = raw.get("market"), raw.get("side"), raw.get("line")
        leg = None
        family = FAMILY_UNKNOWN
        if ref and line is not None:
            if market == "total":
                family = FAMILY_NFL_TOTAL
                leg = (_gt_interval(float(line), inclusive=False) if side == "over"
                       else _lt_interval(float(line), inclusive=False))
            elif market == "spread":
                family = FAMILY_NFL_SPREAD
                team_code = (home[:1] if side == "home" else away[:1])
                ref_code = sorted(set(codes))[0] if ref else None
                if team_code and ref_code:
                    leg = _spread_interval(team_code[0], float(line), ref_code)
        push = _book_push_leg(leg, line) if leg else None
        return EventIdentity(family if leg else FAMILY_UNKNOWN,
                             ref, leg, None, AUTHORITY_NFL, _close_date(m.close_time),
                             push_leg=push)

    blob = " ".join(filter(None, (m.event_title, m.resolution_criteria, m.market_id)))
    codes = _nfl_team_codes(blob)
    ref = _nfl_referent(codes)
    t = blob.lower()
    leg, family = None, FAMILY_UNKNOWN
    if ref:
        is_spread = any(c in t for c in _SPREAD_CUES)
        is_total = any(c in t for c in _TOTAL_CUES)
        if is_spread and not is_total:
            ref_code = sorted(set(codes))[0]
            leg = _nfl_spread_leg(blob, codes, ref_code)
            family = FAMILY_NFL_SPREAD if leg else FAMILY_UNKNOWN
        elif is_total:
            leg = _nfl_total_interval(blob)
            family = FAMILY_NFL_TOTAL if leg else FAMILY_UNKNOWN
    # A Kalshi contract is binary — it resolves Yes or No and never refunds — so its
    # win-or-push interval is exactly its win leg. The push lives only on the book side.
    return EventIdentity(family, ref, leg, None, AUTHORITY_NFL, _close_date(m.close_time),
                         push_leg=leg)


def _looks_like_nfl(m: NormalizedMarket) -> bool:
    if (m.raw or {}).get("source") == "sportsgameodds":
        return True
    blob = " ".join(filter(None, (m.event_title, m.resolution_criteria, m.market_id)))
    return len(_nfl_team_codes(blob)) >= 2


def extract(m: NormalizedMarket) -> EventIdentity:
    """Structured identity for one market. Routes NFL markets to the NFL parser and
    everything else to the Fed parser; the family gate keeps the two axes from ever
    being compared against each other."""
    if _looks_like_nfl(m):
        return _extract_nfl(m)
    return _extract_fed(m)


def _extract_fed(m: NormalizedMarket) -> EventIdentity:
    """Structured identity for one Fed rate-decision market.

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

    # 2. Authority — same settlement source of truth. Runs before the outcome-leg block so a
    #    hard DIFFERENT_QUESTION disqualifier is never short-circuited by a softer SUBTLY
    #    leg-nuance verdict.
    if ia.authority is None or ib.authority is None:
        return IdentityVerdict(DIFFERENT_QUESTION, "authority",
                               "could not confirm a shared settlement authority — fail-closed")
    if ia.authority != ib.authority:
        return IdentityVerdict(DIFFERENT_QUESTION, "authority",
                               f"different settlement authority: {ia.authority} vs {ib.authority}")

    # 3. Close — same resolution window. Also runs before the outcome-leg block: a rematch
    #    (same teams, same leg, different week) must fall out here at "close", not walk into the
    #    wedge table as a SUBTLY leg-nuance disagreement.
    if ia.close_date is None or ib.close_date is None:
        return IdentityVerdict(DIFFERENT_QUESTION, "close",
                               "missing close date on one side — fail-closed")
    da = datetime.fromisoformat(ia.close_date).date()
    db = datetime.fromisoformat(ib.close_date).date()
    if abs((da - db).days) > max_close_gap_days:
        return IdentityVerdict(DIFFERENT_QUESTION, "close",
                               f"close dates {ia.close_date} vs {ib.close_date} differ by more "
                               f"than {max_close_gap_days}d")

    # 4. Outcome leg — the check that catches complements.
    if ia.family in _LEG_FAMILIES:
        if ia.leg is None or ib.leg is None:
            return IdentityVerdict(DIFFERENT_QUESTION, "outcome_leg",
                                   "could not resolve an outcome leg — fail-closed")
        if not _overlaps(ia.leg, ib.leg):
            return IdentityVerdict(
                DIFFERENT_QUESTION, "outcome_leg",
                f"complementary legs: {_leg_label(ia.leg, ia.family)} vs "
                f"{_leg_label(ib.leg, ib.family)} cannot both pay out, so the price "
                f"difference is not a disagreement")
        if ia.leg != ib.leg:
            return IdentityVerdict(
                SUBTLY_DIFFERENT, "outcome_leg",
                f"overlapping but unequal legs: {_leg_label(ia.leg, ia.family)} vs "
                f"{_leg_label(ib.leg, ib.family)} — they settle differently in part of the range")
        # Win legs are identical here. They can still settle differently on a PUSH: a book at
        # an integer key number refunds where a look-alike half-point Kalshi contract pays out
        # or loses outright. Comparing only win intervals would wave this through as SAME and
        # bury the entire push mass at one of the most common margins — the inverse of the
        # complement bug the leg check exists to catch.
        pa = ia.push_leg if ia.push_leg is not None else ia.leg
        pb = ib.push_leg if ib.push_leg is not None else ib.leg
        if pa != pb:
            return IdentityVerdict(
                SUBTLY_DIFFERENT, "outcome_leg",
                f"identical win legs ({_leg_label(ia.leg, ia.family)}) but a push splits them "
                f"at margin {_disputed_ints(pa, pb)}: one side refunds there while the other "
                f"pays out or loses, so the price gap is real, not noise")
    elif ia.level_bound != ib.level_bound:
        return IdentityVerdict(DIFFERENT_QUESTION, "outcome_leg",
                               f"different thresholds: {ia.level_bound}% vs {ib.level_bound}%")

    return IdentityVerdict(SAME_QUESTION, None,
                           f"same referent ({ia.referent}), same leg "
                           f"({_leg_label(ia.leg, ia.family)}), same authority, closes "
                           f"within {max_close_gap_days}d"
                           if ia.leg else f"same referent ({ia.referent}), same threshold")


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

    # Referent-level buckets for the SUBTLY_DIFFERENT sweep, which needs leg *overlap*
    # rather than leg equality and so cannot be answered by an exact key. Keyed by
    # (family, referent) so a Fed meeting and an NFL game never share a bucket.
    by_meeting: dict = {}
    for m, i in ids_b:
        if i.family in _LEG_FAMILIES and i.referent and i.leg:
            by_meeting.setdefault((i.family, i.referent), []).append((m, i))

    same, subtle = [], []
    for a, ia in ids_a:
        if ia.family == FAMILY_UNKNOWN or ia.referent is None or ia.authority is None:
            continue
        key = (ia.family, ia.referent, ia.leg, ia.level_bound, ia.authority)
        for b, ib in index.get(key, ()):
            v = compare(ia, ib, max_close_gap_days)
            if v.is_same:
                same.append((a, b, v))
            elif v.status == SUBTLY_DIFFERENT:
                # Same win-leg index bucket, but compare() found a push splitting them. This is
                # the book-integer-vs-Kalshi-half-point wedge; it never reaches the overlap
                # sweep below (that skips equal legs), so surface it here or it vanishes.
                subtle.append((a, b, v))

        if ia.family in _LEG_FAMILIES and ia.leg:
            for b, ib in by_meeting.get((ia.family, ia.referent), ()):
                if ib.leg == ia.leg:
                    continue              # already handled by the exact join
                v = compare(ia, ib, max_close_gap_days)
                if v.status == SUBTLY_DIFFERENT:
                    subtle.append((a, b, v))

    return same, subtle
