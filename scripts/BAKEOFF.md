# Odds-source bake-off — SportsGameOdds vs OddsPapi

Phase 1 of the Kalshi-NFL pivot. Goal: pick ONE free-tier odds source to devig against
Kalshi NFL totals/spreads. Decision criteria: clean full-game totals + spreads, named
bookmakers (Pinnacle ideally present), a schema we can decode deterministically, and a
free tier that survives a daily scan.

> **Status: probes written, NOT yet run against live data.**
> `SGO_API_KEY` and `ODDSPAPI_API_KEY` are both unset in the environment, so the numbers
> below are from the two providers' published docs (verified 2026-08-08), not from a live
> keyed call. Export the keys and run both probes to replace this with observed data
> before locking the pick. The recommendation is preliminary but the structural gap is
> documented, not guessed.

Run to confirm:
```bash
export SGO_API_KEY=...        # then:
python3 scripts/sgo_probe.py
export ODDSPAPI_API_KEY=...    # then:
python3 scripts/oddspapi_probe.py
```

---

## Side by side (from docs, pending live confirmation)

| Dimension | SportsGameOdds | OddsPapi |
|---|---|---|
| NFL endpoint | `GET /v2/events?leagueID=NFL&oddsAvailable=true` — one call returns games **with odds inline** | Two-step: `GET /fixtures?sportId=14` then `GET /fixtures/odds?fixtureId=X` per game |
| Schema shape | **Self-describing.** oddID = `points-all-game-ou-over` etc. — market, side, and line are readable off the key | **Opaque.** odds keyed by integer `outcomeId`; you must join a separate market dictionary to learn what each id means and what line it carries |
| Odds format | American (documented), per-book map inside each odds entry | Decimal (e.g. 1.91), keyed bookmakerSlug → outcomeId → {odds, changedAt} |
| Named bookmakers | Yes — per-book map with names; Pinnacle expected present (confirm in probe) | Yes — bookmakerSlug keys; Pinnacle presence TBD in probe |
| Free tier | **2,500 objects / month, 10 req/min** | **250 requests / MONTH** |
| Free-tier freshness | **~10-minute delay, 9 books** (confirm in probe) | Delay TBD in probe — assume non-real-time on free tier |
| Cost to run a daily scan | 1 events call pulls many games at once → cheap per game | 1 + N calls per scan (one odds call PER game) → 250/mo cap is exhausted fast |
| Decode work for us | Low — parse the oddID string, done | High — maintain/refresh an outcomeId→meaning dictionary, and it can drift |

## Why this matters for the identity gate

Phase 4 extends `identity.py` to read a leg-interval (`over 45.5` → `(45.5, ∞)`) off each
market. That parse is trivial when the line lives **in the key** (SGO) and becomes a
second lookup-and-join problem when the line lives behind an **opaque id** (OddsPapi).
Every extra decode step is a new fail-closed branch and a new way for a live contract to
go unmatched — working directly against the ≥80% match success metric.

The 250-requests/**month** OddsPapi cap is the harder blocker: at one odds call per game,
a single full slate's scan (~16 games) is ~16 requests, so a daily scan blows the monthly
budget inside two weeks. SGO's 2,500 objects/month + 10 req/min is built for exactly this
repeated-poll pattern.

## Freshness — the dimension this bake-off originally under-weighted

The first cut of this doc graded schema, quota, and call-convenience and ignored **data
latency**, which is the dimension that actually decides whether an output number is real.
On the free tier both providers serve delayed lines (~10 min for SGO). NFL lines move on
injury/steam in seconds, so a delayed book line vs. a live Kalshi price does not measure
fair-value divergence — it measures time skew. That is the same artifact category the
identity gate exists to reject, except baked into the input where the gate cannot see it.

Consequence for scope:
- **Live fair-value gaps** (book fair prob vs Kalshi price) require real-time sharp data
  to mean anything. Real-time NFL ≈ **$99/mo** across providers. Do NOT trust a gap number
  produced off free/delayed data, and do not budget the $99/mo until a thesis earns it.
- **Key-number / push structural mismatches** are latency-immune: they turn on contract
  *structure* (is a push live at this integer?), not on the live price. That signal is
  validatable on free/delayed data. This is the demo we build first.

So SGO's free tier is fine for the push-structure demo and insufficient for any
trustworthy fair-value claim. Both statements are true at once; keep them separate.

## Recommendation (preliminary): **SportsGameOdds**

- Self-describing oddIDs → the leg/line parse the gate needs is a string split, not a
  dictionary join. Fewer fail-closed branches, higher match rate.
- Free tier fits a daily NFL scan; OddsPapi's 250/mo does not.
- Games+odds in one call → simpler adapter, fewer round-trips, less to break.

Open items to confirm on the live run (do NOT lock the pick until these are checked):
1. **Pinnacle actually present** in the SGO per-book map for NFL totals/spreads.
2. Full-game total + spread both parse cleanly (period `game`, betType `ou` / `sp`).
3. The per-book inner field names (`odds` / `overUnder` / `spread` / timestamps) match
   what `sgo_probe.py` guesses — the probe dumps one raw entry precisely to confirm this.

If the live SGO run lacks Pinnacle or the totals/spreads don't parse, re-open OddsPapi
despite the request cap. Otherwise, proceed to Phase 2 on SGO.
