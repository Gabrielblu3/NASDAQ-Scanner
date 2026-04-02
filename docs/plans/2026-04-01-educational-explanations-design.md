# Educational Explanations — Design Document

**Date:** 2026-04-01
**Goal:** Make the NASDAQ Volatility Scanner accessible to learners by adding plain-English explanations for signals, indicators, and trading decisions — grounded in the app's actual computed data.

**Target audience:** Someone who understands stocks and basic concepts but is learning technical analysis and options.

**Design principle:** "Explain it to a 5th grader" — short, always-visible summaries with expandable deeper detail. All text dynamically generated from real data, never hardcoded generalizations.

---

## 1. Signal Cards (dashboard.py — SIGNALS tab)

### Always visible: "What's happening" summary
Replace the current jargon-heavy "SIGNAL BASIS" line with a plain-English paragraph generated from the signal's actual indicators. Example:

> "AAPL has been on a hot streak — its momentum score (RSI) hit 74, which means buyers have been aggressive. When stocks get this stretched, they usually cool off. The price is also trading above its normal range. This is a setup to profit from a pullback using put options."

The summary is built dynamically using conditional templates based on which conditions triggered the signal (RSI level, BB %B, IV Rank, vol regime, etc.).

### Expander: "Why this strike price?"
Surfaces the delta-targeting logic already in `signal_generator.py`:
> "We picked $182.50 because it gives delta of -0.30 — for every $1 AAPL drops, your put gains ~$0.30. This balances cost vs. profit potential."

### Expander: "Options Breakdown" (Greeks)
Shows delta, theta, vega, gamma from `options_greeks.py` with one-line translations:
- **Delta (-0.30):** Your put gains ~$0.30 for every $1 the stock drops
- **Theta (-$0.45/day):** Time works against you — this option loses ~$0.45/day
- **Vega (0.12):** If market fear increases, your option becomes more valuable
- **Gamma (0.02):** How fast delta changes as the stock moves

### Expander: "Signal Strength Breakdown"
Shows scoring criteria with points:
> "Strength: STRONG (4/7) — RSI overbought (+2), Price near upper band (+1), High volatility (+1)"

### IV Rank — surfaced as visible metric
Currently buried in rationale text. Show as a card metric with inline explanation:
> "IV Rank: 62 — Options are pricier than usual. Above 50 = the market expects bigger moves."

### Risk context
Each signal card gets a short "What could go wrong" note:
> "Risk: Strong earnings or bullish news could push the price higher despite overbought signals. Use the stop loss at $192.50."

---

## 2. Screener Table (dashboard.py — SCREENER tab)

### Column header help text
Use Streamlit's `help` parameter on `st.column_config` or add a legend row:
- **RSI:** "Momentum score (0-100). Above 70 = overbought, below 30 = oversold"
- **ATR Percentile:** "How volatile this stock is vs. its last 100 days. Higher = more movement"
- **Historical Vol:** "How much the price typically swings per year, as a percent"
- **Regime:** "Volatility level — LOW / NORMAL / HIGH / EXTREME"

### Color legend (always visible, above table)
> "Red RSI = overbought (may drop) · Green RSI = oversold (may bounce) · Regime = how wild the stock is acting"

---

## 3. Market Overview Strip (dashboard.py — metric tiles)

### Dynamic summary sentence (always visible, below the strip)
Generated from actual scan data:
> "Right now, the average momentum across NASDAQ stocks is 58 (neutral). 3 stocks are overbought and could pull back. 0 are oversold. 5 are showing high volatility — bigger swings mean more opportunity but also more risk."

Conditional logic:
- AVG RSI > 60: "The market is leaning overbought — caution on new long positions"
- AVG RSI < 40: "The market is oversold — potential bounce opportunities"
- AVG RSI 40-60: "The market momentum is neutral"
- HIGH VOL > 5: "Elevated volatility across the board — good for options plays but use tight stops"

---

## 4. Accuracy Safeguards

- All explanations dynamically reference the actual computed values (RSI, delta, theta, etc.)
- Conditional language: "tends to," "historically," "often" — never "will" or "guaranteed"
- Risk context on every signal — what could go wrong, not just the bull case
- Greeks pulled from the existing Black-Scholes calculation in `options_greeks.py`
- Data freshness indicator showing when the scan last ran

---

## 5. Implementation Approach

All changes are in `dashboard.py` (~2145 lines) with minor additions to `signal_generator.py` to expose scoring details.

### New helper module: `nasdaq_scanner/explanations.py`
Contains all the plain-English generation logic:
- `generate_signal_summary(signal_data, indicators)` — builds the "What's happening" text
- `generate_strike_explanation(signal_data, greeks)` — builds strike rationale
- `format_greeks_educational(greeks)` — Greeks with plain translations
- `generate_strength_breakdown(signal_data)` — scoring criteria display
- `generate_market_summary(scan_results)` — market strip summary
- `generate_risk_note(signal_data)` — "What could go wrong"

### Changes to existing files:
- **`signal_generator.py`**: Expose the scoring breakdown (which conditions triggered, how many points each) in the signal dict
- **`dashboard.py`**: Add expanders to signal cards, column help to screener, summary below market strip, import explanations module

### No changes to:
- `technical.py`, `volatility.py`, `options_greeks.py` — calculation logic stays untouched
- `market_data.py`, `options_data.py` — data fetching stays the same
- `stock_screener.py` — filtering logic unchanged

---

## 6. Verification

- Run the dashboard locally with `streamlit run nasdaq_scanner/dashboard.py`
- Trigger a scan and verify:
  - Signal cards show plain-English summary + working expanders
  - Greeks display real computed values, not placeholders
  - Screener columns have help tooltips
  - Market strip has a dynamic summary sentence
  - All explanations reference actual data values from the scan
- Test with different scan sizes (Top 20, Top 50, Full 100)
- Test edge case: no signals found — verify educational content handles empty state
