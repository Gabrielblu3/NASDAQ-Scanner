# Prediction Terminal — Handoff

Cross-venue prediction-market **signal companion**. Reads the same real-world event on
two venues (Polymarket + Kalshi), reconciles it against the sharpest external reference,
and tells a user who can trade only ONE venue what the divergence means for them.

**Positioning (locked):** signal + decision companion, NOT arb execution. Divergence is
*directional information*, never a "guaranteed arb." The moat is the judgment layer
(`master-prompt.md`), not the data plumbing — the naive cross-venue scanner is a red ocean
and pure arb is mostly un-capturable for retail (fees, KYC, capital lockup, resolution mismatch).

---

## What's here

| File | Role | State |
|------|------|-------|
| `master-prompt.md` | The IP. Step 1-5 reasoning procedure with the fail-closed event-identity gate. | **Done, v0.2.** Validated on WC final / MLS draw / July FOMC. |
| `models.py` | `NormalizedMarket` + `MatchCandidate` shared schema. | Done. |
| `polymarket.py` | Gamma API adapter (public, no auth). | **Live-validated** — pulls ~85 binary markets. |
| `kalshi.py` | trade-api v2 adapter. Handles BOTH host schemas (cents + dollars). | Code done; see host caveat below. |
| `matcher.py` | Crude token-overlap + date-guard candidate filter. | Done. Judgment stays in the prompt, not here. |
| `signal.py` | Loads the prompt, assembles payload, calls Anthropic. | Wired; live API call unexercised (no key in build env). |
| `run.py` | CLI: `--demo`, live matching, `--signal N`. | Runs end-to-end. |
| `examples/fomc_july2026.json` | Validated real-data payoff case. | Done. |

## Run it

```bash
pip install -r requirements.txt          # only dep is `anthropic`
python run.py --demo                      # full Step 1-5 loop on the validated FOMC case
python run.py                             # live: fetch both venues, list divergence candidates
export ANTHROPIC_API_KEY=...              # then --demo / --signal actually call the model
```

Without the key, `--demo` prints the fully-assembled prompt payload (exactly what the model
receives) so the plumbing is verifiable without credentials.

## Proven vs. stubbed

**Proven end-to-end:**
- Polymarket adapter pulls live binary markets and normalizes prices (0-1) correctly.
- Kalshi adapter normalizes both schemas (production cents / elections dollars).
- Matcher narrows thousands of markets to candidate pairs; empty result is honest, not a crash.
- The signal runner assembles the correct payload and is wired to the model.
- The *thesis* itself is validated on real data (see `master-prompt.md` "Validated on").

**Stubbed / deferred:**
- The live Anthropic call is unexercised here (no API key in the build env). Code path is complete.
- Kalshi live cross-match — blocked by the host caveat below.
- Everything downstream of the signal (UI, delivery form, more venues) — intentionally not built.

## ⚠️ Kalshi host caveat (the one thing to fix first)

Production `api.kalshi.com` is **network-unreachable from the build box** (HTTP 000,
independent of the Claude sandbox). The reachable `api.elections.kalshi.com` host serves
general markets but, as of 2026-07-17, only illiquid combo/parlay markets are priced there —
NOT the clean single markets (Fed/macro/marquee) worth cross-matching with Polymarket.

**Action for Gabriel:** run on a box where `api.kalshi.com` resolves, flip `KALSHI_BASE` in
`kalshi.py` to production, and confirm which host carries the target series. The adapter
already handles the production cents schema — no code change beyond the base URL.

## Open questions (Gabriel owns downstream)

1. **Delivery form** — browser extension vs. standalone vs. digest. Deliberately deferred; the
   backend (adapters + normalization + matcher + master prompt) is shared regardless.
2. **More venues** — v1 is Polymarket + Kalshi only. Add adapters against the same
   `NormalizedMarket` schema; nothing else changes.
3. **Sharp-reference automation** — sportsbook no-vig (sports), CME FedWatch (macro) are
   currently hand-supplied in the payload. Auto-fetching them is the next real feature.
4. **The WTP question is still open.** Before heavy investment, the cheap validation is a
   10-20 user concierge test (manually send divergence calls, see if anyone would pay). Building
   the platform is not the same as proving demand — that stays true regardless of how clean this code is.

## Where the edge actually lives (don't over-promise)

Marquee liquid events are efficient (price ≈ sharp no-vig — WC final validated PM 59.2% vs
Pinnacle 59.3%). Real edge concentrates in **inefficiency pockets**: thin/less-liquid markets,
news-lag windows, and non-sports domains where venues genuinely disagree. Pure geopolitics has
NO sharp reference — deepest pocket, lowest confidence. The prompt is built to say "no edge"
on the efficient stuff; that honesty is the product, not a bug.
