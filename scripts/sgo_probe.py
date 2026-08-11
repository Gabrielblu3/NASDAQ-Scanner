#!/usr/bin/env python3
"""Probe: SportsGameOdds NFL totals + spreads coverage (Phase 1 bake-off).

Purpose is DIAGNOSTIC, not production. It answers three questions the bake-off needs:
  1. Does the free tier return live NFL games with full-game totals and spreads?
  2. Which bookmakers are present, and is Pinnacle among them?
  3. What does the payload actually look like (odds format, field names, quirks)?

Docs (verified 2026-08-08):
  GET https://api.sportsgameodds.com/v2/events?apiKey=KEY&leagueID=NFL&oddsAvailable=true
  Auth: `apiKey` query param. Free tier: 2500 objects/month, 10 req/min.
  Odds live under event["odds"], keyed by an oddID of the form
      {statID}-{statEntityID}-{periodID}-{betTypeID}-{sideID}
  e.g. points-all-game-ou-over / points-all-game-ou-under (game total),
       and a spread betType (typically -sp-) with home/away sides.
  Per-book prices live under each odds entry (byBookmaker-style map). Exact inner
  field names are NOT fully documented, so this probe DUMPS a raw sample rather than
  trusting a hard-coded schema — read the dump to confirm the real shape.

Never fabricates: if the call fails or returns empty, it says so and exits non-zero.
Only stdlib (urllib) — matches kalshi.py / polymarket.py, no new dependency.
"""

from __future__ import annotations

import json
import os
import sys
from urllib.request import urlopen, Request
from urllib.parse import urlencode
from urllib.error import HTTPError, URLError

BASE = "https://api.sportsgameodds.com"
KEY = os.environ.get("SGO_API_KEY")
MAX_GAMES = 6          # keep object spend low against the 2500/mo free cap


def _get(path: str, params: dict) -> dict:
    url = f"{BASE}{path}?{urlencode(params)}"
    req = Request(url, headers={"User-Agent": "prediction-terminal-probe/0"})
    with urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode())


def _unwrap(payload):
    """SGO wraps list results as {success, data:[...]}; tolerate a bare list too."""
    if isinstance(payload, dict):
        return payload.get("data", payload.get("events", []))
    return payload if isinstance(payload, list) else []


def _oddid_parts(odd_id: str) -> dict:
    p = odd_id.split("-")
    if len(p) < 5:
        return {}
    return {"statID": p[0], "entity": p[1], "period": p[2],
            "betType": p[3], "side": p[4]}


def _books(entry: dict) -> dict:
    """Best-effort: find the per-bookmaker price map inside an odds entry.

    Documented as a byBookmaker-style map; we probe a few likely keys and, failing
    that, return {} so the caller reports 'schema unclear — see raw dump'.
    """
    for k in ("byBookmaker", "bookmakers", "books", "byBook"):
        v = entry.get(k)
        if isinstance(v, dict) and v:
            return v
    return {}


def _price_and_line(book_entry: dict):
    """Pull a human-readable (price, line, timestamp) from one book's odds object,
    trying the documented-ish field names. Returns strings/None; never guesses a number."""
    if not isinstance(book_entry, dict):
        return (str(book_entry), None, None)
    price = book_entry.get("odds") or book_entry.get("price") or book_entry.get("american")
    line = (book_entry.get("overUnder") or book_entry.get("spread")
            or book_entry.get("line") or book_entry.get("handicap"))
    ts = book_entry.get("lastUpdatedAt") or book_entry.get("updatedAt") or book_entry.get("changedAt")
    return (price, line, ts)


def main() -> int:
    if not KEY:
        print("SGO_API_KEY not set. export SGO_API_KEY=... and re-run.", file=sys.stderr)
        return 2

    print(f"=== SportsGameOdds probe :: {BASE}/v2/events leagueID=NFL ===\n")
    try:
        payload = _get("/v2/events", {"apiKey": KEY, "leagueID": "NFL",
                                      "oddsAvailable": "true", "limit": MAX_GAMES})
    except (HTTPError, URLError) as e:
        code = getattr(e, "code", "n/a")
        print(f"REQUEST FAILED (http {code}): {e}", file=sys.stderr)
        return 1

    events = _unwrap(payload)
    if not events:
        print("0 events returned. Top-level keys:", list(payload)[:10]
              if isinstance(payload, dict) else type(payload).__name__)
        print("Nothing to characterize — surfacing honestly rather than inventing data.")
        return 1

    print(f"events returned: {len(events)}\n")
    dumped_raw = False

    for ev in events:
        home = ev.get("homeTeam") or ev.get("home") or {}
        away = ev.get("awayTeam") or ev.get("away") or {}
        teams = ev.get("name") or f"{away.get('name', away) } @ {home.get('name', home)}"
        start = ev.get("startsAt") or ev.get("startTime") or ev.get("scheduled") or "?"
        odds = ev.get("odds") or {}
        print(f"--- {teams}   start={start}   odds_entries={len(odds)}")

        if not isinstance(odds, dict) or not odds:
            print("    no odds object on this event\n")
            continue

        # Dump ONE raw entry so the true inner schema is visible (do this once).
        if not dumped_raw:
            sample_key = next(iter(odds))
            print("    [raw sample odds entry — confirm real schema against this]")
            print("    " + json.dumps({sample_key: odds[sample_key]}, indent=2)[:900].replace("\n", "\n    "))
            print()
            dumped_raw = True

        # Group full-game totals (ou) and spreads (sp/ps) by their side.
        totals, spreads, book_set = {}, {}, set()
        for oid, entry in odds.items():
            parts = _oddid_parts(oid)
            if parts.get("period") not in ("game", "reg", "fulltime", None):
                continue
            bt, side = parts.get("betType"), parts.get("side")
            books = _books(entry) if isinstance(entry, dict) else {}
            book_set.update(books.keys())
            if bt == "ou":
                totals.setdefault(side, (oid, entry, books))
            elif bt in ("sp", "ps", "spread"):
                spreads.setdefault(side, (oid, entry, books))

        pin = [b for b in book_set if "pinnacle" in b.lower()]
        print(f"    bookmakers seen: {len(book_set)}  pinnacle={'YES ' + str(pin) if pin else 'no'}")

        for label, mkt in (("TOTAL", totals), ("SPREAD", spreads)):
            if not mkt:
                print(f"    {label}: none parsed")
                continue
            for side, (oid, entry, books) in mkt.items():
                shown = []
                for bname, be in list(books.items())[:4]:
                    price, line, ts = _price_and_line(be)
                    shown.append(f"{bname}={price}@{line}")
                print(f"    {label} {side:<5} [{oid}] :: " + ", ".join(shown) if shown
                      else f"    {label} {side:<5} [{oid}] :: (no per-book prices — see raw dump)")
        print()

    print("done. Read the raw sample above to lock the exact field names before Phase 2.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
