"""SportsGameOdds adapter — NFL full-game totals + spreads as NormalizedMarket sides.

A sportsbook line is a venue like any other: this adapter absorbs SGO's quirks and emits
the same NormalizedMarket schema every other adapter does, so the identity gate and the
devig step never see SGO-specific field names.

Design:
  - `parse_event(ev)` is PURE — given one SGO event dict it returns a list of
    NormalizedMarket sides. No network, so it is unit-testable offline against a captured
    fixture (which matters because SGO_API_KEY may not be set).
  - `fetch_markets()` is the thin networked wrapper: GET /v2/events, then parse_event each.

One side = one NormalizedMarket. A full-game total yields two sides (over / under); a
spread yields two (home / away). `implied_prob` is the reference book's price WITH VIG
STILL IN — devig.py strips the vig later using both sibling sides. We pick ONE reference
book per market (Pinnacle if it quotes both sides, else any book that quotes both) so the
two sides come from the same book at the same line, which is what multiplicative devig
requires. The chosen book, line, and structured game identity are stashed in `raw` for the
NFL identity gate (Phase 4) and the devig pairing (Phase 5).

SGO odds live under event["odds"], keyed by an oddID:
    {statID}-{statEntityID}-{periodID}-{betTypeID}-{sideID}
  e.g. points-all-game-ou-over / points-all-game-ou-under (game total),
       and a spread betType (sp/ps) with home/away sides.
Inner per-book field names are NOT fully documented — this adapter probes the likely keys
defensively (same posture as scripts/sgo_probe.py) rather than trusting a hard schema.

Never fabricates: a missing key raises; unparseable odds are skipped, not guessed.
Only stdlib (urllib) — no new dependency.
"""

from __future__ import annotations

import json
import os
from typing import List, Optional, Dict, Tuple
from urllib.request import urlopen, Request
from urllib.parse import urlencode

from models import NormalizedMarket

SGO_BASE = "https://api.sportsgameodds.com"
SGO_API_KEY_ENV = "SGO_API_KEY"
PREFERRED_BOOK = "pinnacle"        # the sharp book we most want to devig against
MAX_GAMES = 16                     # a full NFL slate; stays well under the free-tier cap

# SGO periodIDs that mean "the whole game" (not a quarter/half). None tolerates events
# whose oddID omits the period segment.
GAME_PERIODS = ("game", "reg", "fulltime", None)


# --------------------------------------------------------------------------- units
def _num(v) -> Optional[float]:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _odds_to_prob(v) -> Optional[float]:
    """American OR decimal odds -> implied probability (0-1), vig included.

    American odds are always |x| >= 100 by definition, so anything in (1, 100) is a decimal
    quote. This disambiguates without trusting a field name.
    """
    x = _num(v)
    if x is None:
        return None
    if 1.0 < x < 100.0:                 # decimal odds (e.g. 1.91)
        return 1.0 / x
    if x >= 100.0:                      # positive American (e.g. +120)
        return 100.0 / (x + 100.0)
    if x <= -100.0:                     # negative American (e.g. -110)
        return (-x) / ((-x) + 100.0)
    return None                         # 0, or nonsensical |x|<100 non-decimal


def _book_prob(be) -> Optional[float]:
    """Implied prob from one book's odds object. Prefers an explicit decimal field, then
    the documented-ish american/odds/price fields. Scalars are tolerated too."""
    if isinstance(be, dict):
        dec = _num(be.get("decimal") or be.get("decimalOdds"))
        if dec and dec > 1.0:
            return 1.0 / dec
        return _odds_to_prob(be.get("odds") or be.get("american")
                             or be.get("oddsAmerican") or be.get("price"))
    return _odds_to_prob(be)


def _book_line(be) -> Optional[float]:
    if not isinstance(be, dict):
        return None
    return _num(be.get("overUnder") or be.get("spread")
                or be.get("line") or be.get("handicap"))


# --------------------------------------------------------------------------- schema probes
def _books(entry: dict) -> dict:
    """The per-bookmaker price map inside one odds entry (byBookmaker-style)."""
    if not isinstance(entry, dict):
        return {}
    for k in ("byBookmaker", "bookmakers", "books", "byBook"):
        v = entry.get(k)
        if isinstance(v, dict) and v:
            return v
    return {}


def _oddid_parts(odd_id: str) -> dict:
    p = odd_id.split("-")
    if len(p) < 5:
        return {}
    return {"statID": p[0], "entity": p[1], "period": p[2],
            "betType": p[3], "side": p[4]}


def _market_of(bet_type: Optional[str]) -> Optional[str]:
    if bet_type == "ou":
        return "total"
    if bet_type in ("sp", "ps", "spread"):
        return "spread"
    return None


# --------------------------------------------------------------------------- event meta
def _team_name(t) -> str:
    if isinstance(t, dict):
        return str(t.get("name") or t.get("abbreviation") or t.get("shortName")
                   or t.get("teamID") or t)
    return str(t)


def _event_meta(ev: dict) -> Tuple[str, str, str, str]:
    """Return (away, home, start, game_id). Best-effort across SGO field spellings."""
    home = _team_name(ev.get("homeTeam") or ev.get("home") or {})
    away = _team_name(ev.get("awayTeam") or ev.get("away") or {})
    start = (ev.get("startsAt") or ev.get("startTime")
             or ev.get("scheduled") or ev.get("date") or "")
    game_id = str(ev.get("eventID") or ev.get("id") or f"{away}@{home}:{start}")
    return away, home, start, game_id


# --------------------------------------------------------------------------- reference book
def _choose_book(sides: Dict[str, Dict[str, Tuple[float, Optional[float]]]]) -> Optional[str]:
    """Pick one book present on BOTH sides so devig strips vig from a coherent pair.

    Prefer Pinnacle (sharpest). `sides` maps side -> {book: (prob, line)}.
    """
    book_sets = [set(bm.keys()) for bm in sides.values() if bm]
    if len(book_sets) < 2:              # need a real two-sided market
        return None
    common = set.intersection(*book_sets)
    if not common:
        return None
    for b in common:
        if PREFERRED_BOOK in b.lower():
            return b
    return sorted(common)[0]


# --------------------------------------------------------------------------- pure core
def parse_event(ev: dict) -> List[NormalizedMarket]:
    """PURE: one SGO event dict -> list of NormalizedMarket sides (no network)."""
    odds = ev.get("odds")
    if not isinstance(odds, dict) or not odds:
        return []
    away, home, start, game_id = _event_meta(ev)

    # market -> side -> book -> (prob, line)
    collected: Dict[str, Dict[str, Dict[str, Tuple[float, Optional[float]]]]] = {
        "total": {}, "spread": {}}
    for oid, entry in odds.items():
        parts = _oddid_parts(oid)
        if parts.get("period") not in GAME_PERIODS:
            continue
        market = _market_of(parts.get("betType"))
        side = parts.get("side")
        if market is None or not side:
            continue
        for book, be in _books(entry).items():
            prob = _book_prob(be)
            if prob is None:
                continue
            collected[market].setdefault(side, {})[book] = (prob, _book_line(be))

    out: List[NormalizedMarket] = []
    for market, sides in collected.items():
        book = _choose_book(sides)
        if book is None:
            continue
        for side, bookmap in sides.items():
            if book not in bookmap:
                continue
            prob, line = bookmap[book]
            out.append(_make_side(market, side, prob, line,
                                  away, home, start, game_id, book))
    return out


def _make_side(market: str, side: str, prob: float, line: Optional[float],
               away: str, home: str, start: str, game_id: str, book: str
               ) -> NormalizedMarket:
    line_s = "?" if line is None else f"{line:g}"
    if market == "total":
        title = f"Total points {side} {line_s} in {away} @ {home}"
        outcome = f"{side} {line_s}"
    else:
        title = f"{side} spread {line_s} in {away} @ {home}"
        outcome = f"{side} {line_s}"
    return NormalizedMarket(
        venue="sportsbook",
        market_id=f"{game_id}:{market}:{side}",
        event_title=title,
        outcome=outcome,
        implied_prob=prob,                 # vig-in; devig.py strips it later
        resolution_criteria="",
        settlement_source=f"sportsgameodds:{book}",
        close_time=start,
        raw={"source": "sportsgameodds", "game_id": game_id,
             "away": away, "home": home, "start": start,
             "market": market, "side": side, "line": line, "book": book},
    )


# --------------------------------------------------------------------------- network
def _get(path: str, params: dict) -> dict:
    url = f"{SGO_BASE}{path}?{urlencode(params)}"
    req = Request(url, headers={"User-Agent": "prediction-terminal/0.2"})
    with urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode())


def _unwrap(payload):
    if isinstance(payload, dict):
        return payload.get("data", payload.get("events", []))
    return payload if isinstance(payload, list) else []


def fetch_markets(limit: int = MAX_GAMES,
                  api_key: Optional[str] = None) -> List[NormalizedMarket]:
    """Fetch NFL games with odds and flatten to NormalizedMarket sides.

    Raises RuntimeError if no API key is available — never fabricates data.
    """
    key = api_key or os.environ.get(SGO_API_KEY_ENV)
    if not key:
        raise RuntimeError(
            f"{SGO_API_KEY_ENV} not set — cannot fetch live odds. "
            f"export {SGO_API_KEY_ENV}=... and retry.")
    payload = _get("/v2/events", {"apiKey": key, "leagueID": "NFL",
                                  "oddsAvailable": "true", "limit": limit})
    events = _unwrap(payload)
    out: List[NormalizedMarket] = []
    for ev in events:
        out.extend(parse_event(ev))
    return out


if __name__ == "__main__":
    import sys
    try:
        ms = fetch_markets()
    except RuntimeError as e:
        print(e, file=sys.stderr)
        sys.exit(2)
    except Exception as e:                # network / parse — surface honestly
        print(f"fetch failed: {e}", file=sys.stderr)
        sys.exit(1)
    print(f"sportsbook (SGO): {len(ms)} sides")
    for m in ms[:12]:
        print(f"  {m.implied_prob:>5.3f}  {m.event_title[:64]}  [{m.settlement_source}]")
    if not ms:
        print("  (0 sides — no NFL games with parseable full-game totals/spreads)")
