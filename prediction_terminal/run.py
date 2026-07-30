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
from pathlib import Path

import polymarket
import kalshi
from matcher import match
from models import NormalizedMarket, MatchCandidate
from signal import run_signal

EXAMPLES = Path(__file__).parent / "examples"


def _fetch_both():
    pm = polymarket.fetch_markets(limit=100)
    kl = kalshi.fetch_markets(limit=1000)
    print(f"fetched: polymarket={len(pm)}  kalshi={len(kl)} (host {kalshi.KALSHI_BASE})")
    if not kl:
        print("  note: 0 priced Kalshi markets from this host — point KALSHI_BASE at "
              "production on an unblocked box for live cross-matching. Try --demo meanwhile.")
    return pm, kl


def cmd_live(args):
    pm, kl = _fetch_both()
    candidates = match(pm, kl)
    print(f"\ncandidate cross-venue pairs (sim >= 0.30): {len(candidates)}\n")
    for i, c in enumerate(candidates[:15]):
        gap = "n/a" if c.gap_pp is None else f"{c.gap_pp:>5.1f}pp"
        print(f"[{i}] sim={c.title_similarity:.2f} gap={gap}")
        print(f"     PM: {c.a.event_title[:70]}  ({c.a.implied_prob})")
        print(f"     KL: {c.b.event_title[:70]}  ({c.b.implied_prob})")
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
    args = p.parse_args()

    if args.demo:
        cmd_demo()
    elif args.signal is not None:
        cmd_signal(args.signal)
    else:
        cmd_live(args)


if __name__ == "__main__":
    main()
