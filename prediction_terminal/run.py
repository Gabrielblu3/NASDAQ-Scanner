#!/usr/bin/env python3
"""CLI entrypoint for the cross-venue prediction-market signal companion.

Modes:
  python run.py            live: fetch both venues, match, list top divergence candidates
  python run.py --demo     run the full Step 1-5 signal on the bundled FOMC example
  python run.py --signal N run the signal on live candidate #N from the matched list

Note: live Kalshi reads work against api.elections.kalshi.com, which is production
(see HOST RESOLUTION in kalshi.py) — scope fetches to a series such as KXFEDDECISION.
--demo exercises the full loop on real validated numbers without touching the network.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import polymarket
import kalshi
import sportsbook
import devig
import keynumbers
import identity
from models import NormalizedMarket, MatchCandidate
from signal import run_signal

EXAMPLES = Path(__file__).parent / "examples"
UNMATCHED_LOG = Path(__file__).parent / "unmatched.log"

# Kalshi's NFL spread and total series. KXNFLGAME is the MONEYLINE series ("will X win the
# game?") — it carries no handicap or total to cross-match against a book line, so pulling it
# was the reason the match came back empty. The 2026-08-10 live pull confirmed spreads live
# under KXNFLSPREAD and totals under KXNFLTOTAL, both quoted at half-points only.
KALSHI_NFL_SERIES = ("KXNFLSPREAD", "KXNFLTOTAL")


# Kalshi series worth cross-matching. An unscoped /markets page returns whatever the
# API happens to serve first — tennis, sports combos, crypto strikes — and yields zero
# Fed candidates, which is what made the live path look empty. KXFEDDECISION carries the
# per-meeting hike/cut/hold legs; KXFED carries the upper-bound-above-X strips, which
# trade year-round rather than only around a decision date.
KALSHI_SERIES = ("KXFEDDECISION", "KXFED")


def _fetch_both():
    """Fetch both venues concurrently, scoped to the series we actually cross-match.

    Nearly all wall-clock here is network wait, so the requests are issued in parallel:
    sequentially this is the sum of every round-trip, concurrently it is the slowest one.
    """
    with ThreadPoolExecutor(max_workers=1 + len(KALSHI_SERIES)) as pool:
        # volume24hr, not lifetime volume — lifetime ordering returns permanently-large
        # markets that have already resolved to ~1%/99%, where nothing can disagree.
        f_pm = pool.submit(polymarket.fetch_markets, limit=100, order="volume24hr")
        f_kl = [pool.submit(kalshi.fetch_markets, limit=200, series_ticker=s)
                for s in KALSHI_SERIES]
        pm = f_pm.result()
        kl = [m for f in f_kl for m in f.result()]

    print(f"fetched: polymarket={len(pm)}  kalshi={len(kl)} "
          f"({'+'.join(KALSHI_SERIES)} @ {kalshi.KALSHI_BASE})")
    if not kl:
        print("  note: 0 priced Kalshi markets for these series — check the series "
              "tickers are still current. --demo runs the full loop offline meanwhile.")
    return pm, kl


def cmd_live(args, show_rejected: bool = False):
    """Fetch, match, then GATE. Only gate-passing pairs are offered as candidates.

    The matcher is a recall filter and cannot tell a disagreement from a complement, so
    everything it returns is a suspect until identity.check clears it. Indices printed
    here are indices into the SURVIVING list — `--signal N` can never address a pair the
    gate rejected.
    """
    pm, kl = _fetch_both()
    same, subtle = identity.pair_markets(pm, kl)

    candidates = [
        MatchCandidate(a=a, b=b, title_similarity=0.0,
                       gap_pp=(None if a.implied_prob is None or b.implied_prob is None
                               else abs(a.implied_prob - b.implied_prob) * 100.0))
        for a, b, _ in same
    ]
    candidates.sort(key=lambda c: (c.gap_pp is None, -(c.gap_pp or 0)))

    print(f"\n{len(same)} same-question pairs, {len(subtle)} flagged subtly-different\n")
    for i, c in enumerate(candidates):
        gap = "n/a" if c.gap_pp is None else f"{c.gap_pp:>5.2f}pp"
        print(f"[{i}] gap={gap}")
        print(f"     PM: {c.a.event_title[:70]}  ({c.a.implied_prob})")
        print(f"     KL: {c.b.event_title[:70]}  ({c.b.implied_prob})")

    if subtle:
        # Shown but never offered as candidates: these are the pairs that look tradeable
        # and settle differently in part of the range — the expensive kind of near-miss.
        print(f"\n  subtly different — NOT tradeable as the same question ({len(subtle)}):")
        for a, b, v in (subtle if show_rejected else subtle[:5]):
            print(f"    {a.event_title[:52]}")
            print(f"      vs {b.event_title[:52]}")
            print(f"      {v.reason[:104]}")
        if not show_rejected and len(subtle) > 5:
            print(f"    ... {len(subtle) - 5} more (--show-rejected)")

    if candidates and args is not None:
        print("\nrun `python run.py --signal 0` to send the top candidate through the master prompt.")
    return candidates


def cmd_signal(index: int):
    candidates = cmd_live(None)
    if index >= len(candidates):
        print(f"\nno candidate #{index} (only {len(candidates)} found).")
        return
    _emit_signal(candidates[index])


def cmd_demo():
    data = json.loads((EXAMPLES / "fomc_july2026.json").read_text())
    a = NormalizedMarket(**data["venue_a"])
    b = NormalizedMarket(**data["venue_b"])
    gap = abs(a.implied_prob - b.implied_prob) * 100.0
    cand = MatchCandidate(a=a, b=b, title_similarity=1.0, gap_pp=gap)
    print("=== DEMO: validated July-2026 FOMC cross-venue case ===")
    print(f"PM no-change {a.implied_prob}  vs  KL no-change {b.implied_prob}  (gap {gap:.1f}pp)\n")
    _emit_signal(cand, data.get("sharp_reference"), data.get("user_position"))


def _emit_signal(cand, sharp=None, position=None):
    result = run_signal(cand, sharp_reference=sharp, user_position=position)
    if result["called_model"]:
        print("--- MODEL VERDICT ---")
        print(result["verdict"])
    else:
        print(f"--- {result['note']} ---")
        print("Assembled prompt payload (this is exactly what the model receives):\n")
        print(json.dumps(result["assembled"], indent=2))


def _fair_values(sb_sides):
    """Devig each game/market's two sides into fair probabilities.

    Returns market_id -> fair_prob. A side is only assigned a fair value when its market has
    exactly two priced sides (over+under, or home+away); anything else is skipped, never
    guessed — the whole point of devig is that it needs both sides of the same book line.
    """
    groups = defaultdict(list)
    for s in sb_sides:
        groups[(s.raw.get("game_id"), s.raw.get("market"))].append(s)
    fair = {}
    for sides in groups.values():
        priced = [s for s in sides if s.implied_prob is not None]
        if len(priced) != 2:
            continue
        for s, f in zip(priced, devig.devig_multiplicative([s.implied_prob for s in priced])):
            fair[s.market_id] = f
    return fair


def _wedge_rows(subtle):
    """Key-number push mismatches: SUBTLY_DIFFERENT NFL *spread* pairs, ranked by the
    outcome mass sitting on the disputed margins.

    This is the wedge — the one signal that survives free/delayed data, because it turns on
    contract STRUCTURE (which integer margins the two sides settle differently on) and a
    stable historical margin distribution, not on a live price gap. A pair that disagrees
    only when the game lands on margin 3 is a real edge; one that disagrees on margin 17 is
    noise. keynumbers.contested_mass draws that line, PUSHES INCLUDED: the dominant case is a
    book integer key number that refunds where the look-alike Kalshi half-point contract does
    not, so the win legs are identical and only the win-or-push legs diverge. Totals are
    excluded: the static prior is a margin-of-victory distribution, so only spreads are scored.
    """
    rows = []
    for k, s, _ in subtle:
        ik, isb = identity.extract(k), identity.extract(s)
        if ik.family != identity.FAMILY_NFL_SPREAD or ik.leg is None or isb.leg is None:
            continue
        mass, margins = keynumbers.contested_mass(
            ik.leg, ik.push_leg or ik.leg, isb.leg, isb.push_leg or isb.leg)
        if not margins:
            continue
        keys = sorted({abs(m) for m in margins})
        rows.append((k.event_title, k.implied_prob, keys, mass * 100.0))
    rows.sort(key=lambda r: -r[3])
    return rows


def _push_risk_label(book_ident):
    """Plain-language 'what the matched book line refunds' — the push-risk read, shown on
    every matched line whether or not there's an edge. Push risk lives on the BOOK side of the
    pair: a Kalshi contract is binary and never refunds, so it carries none. When the matched
    book spread is an integer key number it refunds at exactly that margin, which a look-alike
    half-point Kalshi contract does NOT give back — we name that margin and how often games
    land there. A half-point book line (no push) or a non-spread reads '-'. Never an edge
    claim; literacy about where the two contracts quietly differ."""
    if book_ident.family != identity.FAMILY_NFL_SPREAD or book_ident.leg is None:
        return "-"
    if book_ident.push_leg is None or book_ident.push_leg == book_ident.leg:
        return "-"                                  # half-point book line — nothing to push on
    disputed = keynumbers.disputed_margins(book_ident.leg, book_ident.push_leg)
    if not disputed:
        return "-"
    m = disputed[0]
    return f"book pushes |{abs(m)}| ~{keynumbers.margin_prob(m) * 100:.0f}%"


def _unmatched_reason(k, sb_sides):
    """Why one Kalshi NFL contract found no sportsbook counterpart — for unmatched.log."""
    ik = identity.extract(k)
    if ik.family == identity.FAMILY_UNKNOWN or ik.referent is None:
        return "no NFL total/spread leg parseable from title"
    same_game = [s for s in sb_sides
                 if identity.extract(s).referent == ik.referent]
    if not same_game:
        return f"no sportsbook market for game {ik.referent}"
    # Report the gate's own reason against the closest same-game side.
    return identity.check(k, same_game[0]).reason


def cmd_nfl():
    """Kalshi NFL assistant. Leads with the KEY-NUMBER PUSH MISMATCHES (the wedge), then
    shows commodity fair value as supporting context.

    Section 1 (wedge): spread contracts where Kalshi and the book settle differently on a
    key margin (Kalshi 'win by more than 3' has no push; the book at -3 refunds it), ranked
    by the outcome mass on the disputed margins. This is the latency-immune signal.

    Section 2 (context): kalshi_contract | kalshi_price | fair_value | gap_pp for cleanly
    matched pairs. HONEST CAVEAT — on free/delayed odds these gaps mix real divergence with
    time skew and should not be traded on their own; they are shown for context, not edge.

    Every Kalshi NFL contract that failed to match (with the reason) is logged to
    unmatched.log — that log is the evidence for the >=80% match target either way.
    """
    try:
        sb = sportsbook.fetch_markets()
    except RuntimeError as e:                 # missing SGO key — surface honestly
        print(e)
        print("Cannot run the NFL match without sportsbook odds. Set SGO_API_KEY and retry.")
        return
    except Exception as e:                     # network / parse
        print(f"sportsbook fetch failed: {e}")
        return

    kl = [m for s in KALSHI_NFL_SERIES
          for m in kalshi.fetch_markets(limit=200, series_ticker=s)]
    print(f"fetched: sportsbook_sides={len(sb)}  kalshi_nfl={len(kl)} "
          f"({'+'.join(KALSHI_NFL_SERIES)} @ {kalshi.KALSHI_BASE})")
    if not kl:
        print(f"  note: 0 Kalshi NFL contracts for series {'+'.join(KALSHI_NFL_SERIES)} — "
              f"confirm the series tickers are current before trusting the match rate.")
    if not sb:
        print("  note: 0 sportsbook sides parsed — no NFL games with full-game totals/spreads.")

    fair = _fair_values(sb)
    same, subtle = identity.pair_markets(kl, sb)

    # --- Section 1: the wedge (key-number push mismatches) ---
    wedge = _wedge_rows(subtle)
    print(f"\n=== key-number push mismatches ({len(wedge)}) — structural, latency-immune ===")
    print("  mass_pp uses a REGULAR-SEASON margin prior; preseason margins don't follow it, so "
          "treat mass as directional until the regular season (~Sept 10)")
    if wedge:
        print(f"{'kalshi_contract':<52} | {'kl_price':>8} | {'push@|margin|':>13} | {'mass_pp':>7}")
        print("-" * 90)
        for title, price, keys, mass in wedge:
            pcol = "n/a" if price is None else f"{price:.3f}"
            print(f"{title[:52]:<52} | {pcol:>8} | {','.join(map(str, keys)):>13} | {mass:>7.2f}")
    else:
        print("  none — no spread pair disagreed on a scoreable margin "
              "(needs live Kalshi spread wording to exercise).")

    # --- Section 2: always-on per-contract read (the co-pilot literacy layer) ---
    # Shown for EVERY matched contract, edge or not — the everyday reason to keep the tool
    # open. true = book fair prob (vig stripped by devig); vs_fair = what Kalshi asks above or
    # below that; push_risk = where the MATCHED BOOK LINE refunds (the Kalshi side never does).
    # Never a manufactured pick.
    lit = []
    for k, s, _ in same:
        fv = fair.get(s.market_id)
        if fv is None or k.implied_prob is None:
            continue
        risk = _push_risk_label(identity.extract(s))
        lit.append((k.event_title, k.implied_prob, fv, (k.implied_prob - fv) * 100.0, risk))
    lit.sort(key=lambda r: -abs(r[3]))

    print(f"\nper-contract read — {len(lit)} of {len(kl)} matched "
          f"({(len(lit) / len(kl) * 100.0):.0f}%)" if kl else "\nno Kalshi contracts to read")
    print("  true = book fair (vig stripped); vs_fair mixes real divergence with delayed-data "
          "skew on free odds — literacy, not a standalone edge")
    print("  push_risk names where the matched book line refunds — Kalshi is binary and never "
          "pushes, so that mass is only on the book side of the pair")
    if lit:
        print(f"\n{'kalshi_contract':<44} | {'kl_ask':>6} | {'true':>6} | {'vs_fair':>7} | "
              f"{'push_risk':>16}")
        print("-" * 95)
        for title, ask, fv, gap, risk in lit:
            print(f"{title[:44]:<44} | {ask:>6.3f} | {fv:>6.3f} | {gap:>+7.2f} | {risk:>16}")

    matched_ids = {k.market_id for k, _, _ in same}
    unmatched = [k for k in kl if k.market_id not in matched_ids]
    if unmatched:
        with UNMATCHED_LOG.open("w") as fh:
            fh.write(f"# {len(unmatched)} unmatched Kalshi NFL contracts "
                     f"(series {'+'.join(KALSHI_NFL_SERIES)})\n")
            for k in unmatched:
                fh.write(f"{k.market_id}\t{k.event_title}\t{_unmatched_reason(k, sb)}\n")
        print(f"\nlogged {len(unmatched)} unmatched contracts -> {UNMATCHED_LOG}")
    if subtle:
        print(f"({len(subtle)} subtly-different pairs total; spread mismatches surfaced as the "
              f"wedge above, non-scoreable ones held back)")


def main():
    p = argparse.ArgumentParser(description="Cross-venue prediction-market signal companion")
    p.add_argument("--demo", action="store_true", help="run signal on bundled FOMC example")
    p.add_argument("--signal", type=int, metavar="N", help="run signal on live candidate #N")
    p.add_argument("--nfl", action="store_true",
                   help="match live Kalshi NFL contracts to devigged sportsbook fair value")
    p.add_argument("--show-rejected", action="store_true",
                   help="print every gate-rejected pair (for auditing what the gate ate)")
    args = p.parse_args()

    if args.demo:
        cmd_demo()
    elif args.nfl:
        cmd_nfl()
    elif args.signal is not None:
        cmd_signal(args.signal)
    else:
        cmd_live(args, show_rejected=args.show_rejected)


if __name__ == "__main__":
    main()
