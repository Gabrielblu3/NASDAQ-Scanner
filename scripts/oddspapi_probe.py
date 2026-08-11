#!/usr/bin/env python3
"""Probe: OddsPapi NFL totals + spreads coverage (Phase 1 bake-off).

Counterpart to sgo_probe.py. Same three diagnostic questions:
  1. Does the free tier return NFL games with full-game totals and spreads?
  2. Which bookmakers are present, and is Pinnacle among them?
  3. What does the payload actually look like (odds format, field names, quirks)?

Docs (verified 2026-08-08, docs.oddspapi.io/llms-full.txt):
  Base: https://v5.oddspapi.io/en
  Auth: `apiKey` query param. Free tier: 250 requests / MONTH (hard cap — this probe
  spends carefully: one /fixtures call + one /fixtures/odds call per game, capped).
  Flow is TWO-STEP and this is the key quirk:
    GET /fixtures?sportId=14&statusId=0   -> upcoming NFL fixtures (id, teams, start)
    GET /fixtures/odds?fixtureId=X        -> odds for one fixture
  Odds are keyed bookmakerSlug -> marketId -> outcomeId -> {odds, changedAt}.
  outcomeIds are OPAQUE integers: unlike SGO's self-describing oddIDs, you cannot read
  'over 45.5' off the key. You must join against a MARKET DICTIONARY (the markets list on
  the fixture, or a /markets reference call) to learn what each outcomeId means and what
  line it carries. This probe DUMPS the raw shape so that join surface is visible before
  we commit to decoding it. Odds are DECIMAL (e.g. 1.91), not American.

  sportId=14 is NFL per the docs' sport table; statusId=0 is 'not started'. If those IDs
  have drifted, the probe surfaces an empty result honestly rather than inventing games.

Never fabricates: if the call fails or returns empty, it says so and exits non-zero.
Only stdlib (urllib) — matches sgo_probe.py, no new dependency.
"""

from __future__ import annotations

import json
import os
import sys
from urllib.request import urlopen, Request
from urllib.parse import urlencode
from urllib.error import HTTPError, URLError

BASE = "https://v5.oddspapi.io/en"
KEY = os.environ.get("ODDSPAPI_API_KEY")
NFL_SPORT_ID = 14      # per docs sport table
STATUS_NOT_STARTED = 0
MAX_GAMES = 4          # 250 req/MONTH cap is brutal; each game costs 1 odds request


def _get(path: str, params: dict) -> dict:
    url = f"{BASE}{path}?{urlencode(params)}"
    req = Request(url, headers={"User-Agent": "prediction-terminal-probe/0"})
    with urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode())


def _unwrap(payload):
    """OddsPapi wraps list results; tolerate {data:[...]}, {fixtures:[...]}, bare list."""
    if isinstance(payload, dict):
        for k in ("data", "fixtures", "results", "items"):
            v = payload.get(k)
            if isinstance(v, list):
                return v
        return []
    return payload if isinstance(payload, list) else []


def _teams(fx: dict) -> str:
    home = fx.get("homeTeam") or fx.get("home") or fx.get("participant1") or {}
    away = fx.get("awayTeam") or fx.get("away") or fx.get("participant2") or {}
    if isinstance(home, dict):
        home = home.get("name") or home.get("slug") or home
    if isinstance(away, dict):
        away = away.get("name") or away.get("slug") or away
    return fx.get("name") or f"{away} @ {home}"


def _fixture_id(fx: dict):
    return fx.get("id") or fx.get("fixtureId") or fx.get("fixture_id")


def _market_dictionary(odds_payload) -> dict:
    """Best-effort: build outcomeId -> human meaning from any markets list on the payload.

    This is the whole point of the probe — proving how much work decoding OddsPapi's
    opaque outcomeIds actually is. If we can't find a dictionary, we say so.
    """
    if not isinstance(odds_payload, dict):
        return {}
    markets = (odds_payload.get("markets") or odds_payload.get("marketList")
               or odds_payload.get("outcomes") or [])
    out = {}
    if isinstance(markets, list):
        for m in markets:
            if not isinstance(m, dict):
                continue
            oid = m.get("outcomeId") or m.get("id")
            label = (m.get("name") or m.get("label") or m.get("outcome")
                     or m.get("selection"))
            line = m.get("line") or m.get("handicap") or m.get("total")
            if oid is not None:
                out[str(oid)] = (label, line)
    return out


def _books(odds_payload) -> dict:
    """Return the bookmakerSlug -> {...} map from the odds payload."""
    if not isinstance(odds_payload, dict):
        return {}
    for k in ("odds", "bookmakers", "byBookmaker", "prices"):
        v = odds_payload.get(k)
        if isinstance(v, dict) and v:
            return v
    return {}


def main() -> int:
    if not KEY:
        print("ODDSPAPI_API_KEY not set. export ODDSPAPI_API_KEY=... and re-run.",
              file=sys.stderr)
        return 2

    print(f"=== OddsPapi probe :: {BASE} sportId={NFL_SPORT_ID} (NFL) ===\n")
    print("(free tier is 250 req/MONTH — this run spends "
          f"1 + up to {MAX_GAMES} requests)\n")

    try:
        fx_payload = _get("/fixtures", {"apiKey": KEY, "sportId": NFL_SPORT_ID,
                                        "statusId": STATUS_NOT_STARTED})
    except (HTTPError, URLError) as e:
        code = getattr(e, "code", "n/a")
        print(f"FIXTURES REQUEST FAILED (http {code}): {e}", file=sys.stderr)
        return 1

    fixtures = _unwrap(fx_payload)
    if not fixtures:
        print("0 fixtures returned. Top-level keys:",
              list(fx_payload)[:10] if isinstance(fx_payload, dict)
              else type(fx_payload).__name__)
        print("Nothing to characterize — surfacing honestly rather than inventing data.")
        print("(If NFL is mid-offseason or sportId/statusId drifted, this is expected.)")
        return 1

    print(f"fixtures returned: {len(fixtures)} (probing first {MAX_GAMES})\n")
    dumped_raw = False

    for fx in fixtures[:MAX_GAMES]:
        fid = _fixture_id(fx)
        print(f"--- {_teams(fx)}   fixtureId={fid}   start={fx.get('startTime') or fx.get('date') or '?'}")
        if fid is None:
            print("    no fixtureId on this fixture — cannot fetch odds\n")
            continue

        try:
            odds_payload = _get("/fixtures/odds", {"apiKey": KEY, "fixtureId": fid})
        except (HTTPError, URLError) as e:
            code = getattr(e, "code", "n/a")
            print(f"    ODDS REQUEST FAILED (http {code}): {e}\n")
            continue

        if not dumped_raw:
            print("    [raw sample odds payload — confirm real schema against this]")
            print("    " + json.dumps(odds_payload, indent=2)[:1100].replace("\n", "\n    "))
            print()
            dumped_raw = True

        mkt_dict = _market_dictionary(odds_payload)
        books = _books(odds_payload)
        book_names = list(books.keys())
        pin = [b for b in book_names if "pinnacle" in str(b).lower()]
        print(f"    bookmakers seen: {len(book_names)}  "
              f"pinnacle={'YES ' + str(pin) if pin else 'no'}")
        print(f"    market-dictionary entries decoded: {len(mkt_dict)} "
              f"{'(outcomeIds are decodable)' if mkt_dict else '(NO dictionary found — outcomeIds stay opaque, this is the quirk)'}")

        # Show a couple of decoded prices IF we have the dictionary; else show that the
        # raw keys are meaningless without it.
        shown = 0
        for bname, bmarkets in list(books.items())[:2]:
            if not isinstance(bmarkets, dict):
                continue
            for oid, price_obj in list(bmarkets.items())[:4]:
                meaning = mkt_dict.get(str(oid))
                price = (price_obj.get("odds") if isinstance(price_obj, dict)
                         else price_obj)
                if meaning:
                    label, line = meaning
                    print(f"    {bname}: {label}@{line} = {price} (decimal)")
                else:
                    print(f"    {bname}: outcomeId={oid} = {price} (decimal, MEANING UNKNOWN w/o dict)")
                shown += 1
                if shown >= 6:
                    break
            if shown >= 6:
                break
        print()

    print("done. Read the raw sample above — the outcomeId->meaning join is the whole "
          "cost question vs SportsGameOdds.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
