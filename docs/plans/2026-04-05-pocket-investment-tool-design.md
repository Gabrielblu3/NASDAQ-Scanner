# Pocket Investment Tool — Design Document

**Date:** 2026-04-05
**Goal:** Transform the NASDAQ Volatility Scanner from a dashboard into a personal investment tool that teaches while it helps you trade — accessible to a beginner with $1,000 who doesn't know where to start.

**Inspiration:** Duolingo's "learn by doing" model + Robinhood's frictionless execution. The app should feel personal, actionable, and educational simultaneously.

---

## Target User

Someone who:
- Has ~$1,000 to invest
- Interested in options or day trading
- Has seen finance content online but doesn't know where to start
- Wants guidance, not just data
- Wants to learn BY trading, not before trading

---

## Design Principles (Research-Grounded)

### 1. Just-In-Time Education
**Source:** FINRA Investor Education Foundation studies on financial literacy retention.

Explain concepts at the moment they're relevant — not in a tutorial upfront. When a user sees "Theta: -$0.42/day," the explanation is right there: "Your option loses 42 cents every day just from time passing." Users retain this 3-4x better than pre-loaded lessons.

### 2. Progressive Disclosure
**Source:** Nielsen Norman Group UX principles.

Show essential info first, reveal complexity on demand. Each signal card has three layers:
1. **Headline** (always visible): What's happening, what to do, what it costs — 10 seconds
2. **Details** (one tap): Greeks, scoring, strike rationale — deeper understanding
3. **Execution** (one tap): Pre-filled trade, confirm and go

### 3. Show Both Sides of Every Trade
**Source:** Kahneman & Tversky's Prospect Theory; SEC criticism of Robinhood (2021).

Every signal shows potential gain AND potential loss. No hiding the downside. This builds trust and produces better decision-making.

### 4. Reduce Choice Overload
**Source:** Iyengar & Lepper (choice paralysis); Schwartz "Paradox of Choice."

Surface one "Top Pick" signal personalized to the user's profile. Show 2-3 "Also Worth Watching." Collapse the rest. Beginners see one clear action; experienced users expand for the full picture.

### 5. Transparency Builds Trust
**Source:** MIT Fintech Lab studies on recommendation transparency.

Show HOW every signal was scored. The scoring breakdown is visible, not hidden. Users see exactly why the app flagged a trade, which builds trust and teaches them to recognize patterns over time.

---

## Features (Priority Order)

### Feature 1: Onboarding Flow

First-time visitors see a setup screen instead of the dashboard.

**Step 1 — Budget**
- Slider or selection: $500 / $1,000 / $2,500 / $5,000 / $10,000+
- "This helps us show you trades you can actually afford."

**Step 2 — Risk Tolerance**
- Conservative: "I'd rather make small, safe plays"
- Moderate: "I can handle some swings for better returns"
- Aggressive: "Show me everything"

**Step 3 — Experience Level**
- New to investing
- Know stocks, learning options
- Experienced trader

**Step 4 — Trading Account (Optional)**
- Alpaca API key + secret
- Paper Mode or Live Mode — user's free choice, no restrictions
- Paper: "Practice with simulated money. Same real market data, zero risk."
- Live: "Real money. Real trades." + one-time disclaimer confirmation
- Skip: "Just browsing" — full dashboard, no execution, hypothetical sizing

**Storage:** Profile saves to local JSON + `st.session_state`. Persistent between sessions.

**Header badge:** Always shows current mode (PAPER / LIVE / BROWSING).

---

### Feature 2: Personalized Signal Cards

Each signal card adapts to the user's profile.

**"Your Position" block replaces abstract data grid:**
- Cost in their dollars: "~$340 for 1 contract (34% of your $1,000 budget)"
- Upside scenario: "If AAPL drops 3%: you'd profit ~$180"
- Downside scenario: "If it goes wrong: max loss is $340 (the premium)"
- Position sizing never exceeds their budget

**Risk meter (visual bar):**
- Green (< 20% of budget): "Small position — low exposure"
- Yellow (20-40%): "Moderate position"
- Red (> 40%): "Large position — consider sizing down"

**Execution button (three states):**
- Alpaca connected → "Execute Trade" (pre-filled order summary, one tap to confirm)
- Profile but no Alpaca → "Copy Trade Details" (clipboard with step-by-step broker instructions)
- Just browsing → No button, hypothetical sizing only

---

### Feature 3: "Top Pick" Personalization

The hero panel currently shows the strongest signal by raw score. With a profile, it factors in:
- Budget fit (can they afford the trade?)
- Risk tolerance match (conservative users don't see aggressive plays as top pick)
- Signal strength (still matters, but filtered through profile)

Below the hero: "Also Worth Watching" — 2-3 more signals ranked by profile fit.
Below that: "All Signals" — everything else, collapsed by default.

---

### Feature 4: Trade Execution via Alpaca

**Pre-trade flow:**
1. User taps "Execute Trade" on a signal card
2. Order summary appears: symbol, option type (put/call), strike, expiry, quantity, estimated cost
3. Paper mode: "Confirm Paper Trade" button
4. Live mode: "Confirm LIVE Trade" button (red accent) + checkbox "I understand this uses real money"
5. Order placed via Alpaca API
6. Confirmation: "Order submitted — AAPL $180 Put, 1 contract"

**Post-trade:**
- Trade appears in the Tracker tab linked to the original signal
- P&L updates as the position moves

**Alpaca integration:**
- Uses existing `nasdaq_scanner/data/alpaca_client.py` as foundation
- Paper trading: Alpaca paper API endpoint
- Live trading: Alpaca live API endpoint
- Same code, different API keys

---

### Feature 5: AI Chat Assistant

**Location:** Collapsible panel in the sidebar. Accessible from any tab.

**Context it has:**
- User's profile (budget, risk, experience)
- Current scan results and signals
- Trade history
- All educational content from explanations.py

**Behavior:**
- Answers trading questions with personalized context
- Teaches using real signals as examples, not abstract definitions
- Uses the "explain it back" technique — asks what the user thinks before filling in gaps
- Frames as education ("Here's what this means for your situation") not advice ("You should buy this")
- Can give straight answers when the user just wants a quick fact

**Powered by:** Claude API. Requires Anthropic API key (entered in Settings, not onboarding). App works fully without it.

---

### Feature 6: Daily Market Brief

A 2-3 sentence human-readable summary at the top of the dashboard, above the scan controls.

Uses the existing `generate_market_summary()` from explanations.py but expanded:
- What the market is doing today
- What it means for the user's risk level
- Whether it's a "sit tight" or "look for opportunities" kind of day

Generated from the scan data, not an external API.

---

## Build Process

### Phased Rollout

Each feature is built, tested, and approved independently. The app is always in a working state between phases.

| Phase | Feature | Checkpoint Question |
|-------|---------|-------------------|
| 1 | Onboarding flow | "Does this feel welcoming? Is anything confusing?" |
| 2 | Personalized signal cards | "Do the costs/gains make sense for my budget?" |
| 3 | Top Pick ranking | "Does this recommendation feel right?" |
| 4 | Trade execution (Alpaca) | "Was that easy? Did anything feel risky or unclear?" |
| 5 | AI chat assistant | "Did it actually help? Was the answer useful?" |
| 6 | Daily market brief | "Would I read this every day?" |

### Safety Net

- **Each phase = separate git commit.** App is stable between phases.
- **Rollback:** Any phase can be reverted with `git revert` in seconds.
- **Skip and return:** Phases can be skipped and revisited later.
- **Visual review:** App is launched and reviewed after every phase before pushing to GitHub.
- **Gabriel stays in sync:** Only stable, approved changes get pushed.

---

## What We're NOT Building

- ~~Learn mode / Trade mode toggle~~ → unified experience
- ~~XP / streaks / gamification~~ → gimmicky for finance
- ~~Chat-first redesign~~ → app stays primary, chat supplements
- ~~Broker deep-links~~ → Alpaca handles execution, clipboard handles manual
- ~~Multiple broker integrations~~ → Alpaca only for now

---

## File Reference

| File | Role |
|------|------|
| `nasdaq_scanner/dashboard.py` | All UI code — onboarding, signal cards, chat panel |
| `nasdaq_scanner/explanations.py` | Educational text generation (already built) |
| `nasdaq_scanner/scanner/signal_generator.py` | Signal scoring + Greeks (already modified) |
| `nasdaq_scanner/data/alpaca_client.py` | Alpaca API integration (extend for trading) |
| `nasdaq_scanner/config/settings.py` | App configuration |
| `docs/DESIGN_SYSTEM.md` | Visual design reference |
| `docs/plans/2026-04-05-pocket-investment-tool-design.md` | This document |
