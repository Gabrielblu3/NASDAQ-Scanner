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
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import polymarket
import kalshi
import identity
from matcher import _similarity
from models import NormalizedMarket, MatchCandidate
from signal import run_signal

EXAMPLES = Path(__file__).parent / "examples"


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
        MatchCandidate(a=a, b=b, title_similarity=_similarity(a.event_title, b.event_title),
                       gap_pp=(None if a.implied_prob is None or b.implied_prob is None
                               else abs(a.implied_prob - b.implied_prob) * 100.0))
        for a, b, _ in same
    ]
    candidates.sort(key=lambda c: (c.gap_pp is None, -(c.gap_pp or 0)))

    print(f"\n{len(same)} same-question pairs, {len(subtle)} flagged subtly-different\n")
    for i, c in enumerate(candidates):
        gap = "n/a" if c.gap_pp is None else f"{c.gap_pp:>5.2f}pp"
        print(f"[{i}] gap={gap}  (title sim {c.title_similarity:.2f})")
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


def main():
    p = argparse.ArgumentParser(description="Cross-venue prediction-market signal companion")
    p.add_argument("--demo", action="store_true", help="run signal on bundled FOMC example")
    p.add_argument("--signal", type=int, metavar="N", help="run signal on live candidate #N")
    p.add_argument("--show-rejected", action="store_true",
                   help="print every gate-rejected pair (for auditing what the gate ate)")
    args = p.parse_args()

    if args.demo:
        cmd_demo()
    elif args.signal is not None:
        cmd_signal(args.signal)
    else:
        cmd_live(args, show_rejected=args.show_rejected)


if __name__ == "__main__":
    main()
