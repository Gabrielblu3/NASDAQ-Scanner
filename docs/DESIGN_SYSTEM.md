# NASDAQ Scanner — Design System

The single source of truth for all visual decisions. Reference this before editing any UI code.

---

## Philosophy

Inspired by the Succession opening credits and Faction Collective's editorial web design. The aesthetic is "quiet confidence" — oversized typography, restrained color, generous space. The app should feel like a high-end financial editorial, not a hacker terminal. Information is delivered clearly with no visual noise.

**Core principles:**
- Say more with less — whitespace is a design element
- Typography does the heavy lifting, not color or decoration
- Subtle color shifts communicate meaning (signal type, severity)
- Every pixel earns its place

---

## Typography

### Font Stack

| Role | Font | Weight | Fallback |
|------|------|--------|----------|
| Headlines / Titles | **Bebas Neue** | 400 | Arial Narrow, sans-serif |
| Body / Data | **Inter** | 300, 400, 500, 600 | system-ui, sans-serif |
| Monospace (prices, data) | **JetBrains Mono** | 400, 500 | Consolas, monospace |

**Google Fonts import:**
```
https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Inter:wght@300;400;500;600&family=JetBrains+Mono:wght@400;500&display=swap
```

### Why Bebas Neue
Closest free match to the Succession credits feel — all-caps, condensed, commanding. Wide letter-spacing gives it the engraved, authoritative quality of Sackers Gothic without the licensing cost.

### Type Scale

| Element | Font | Size | Weight | Letter-spacing | Transform |
|---------|------|------|--------|----------------|-----------|
| Page title | Bebas Neue | 72px | 400 | 0.12em | uppercase |
| Section header | Bebas Neue | 36px | 400 | 0.08em | uppercase |
| Tab label | Bebas Neue | 20px | 400 | 0.06em | uppercase |
| Card title (ticker) | Bebas Neue | 28px | 400 | 0.04em | uppercase |
| Body text | Inter | 15px | 400 | 0.01em | none |
| Educational text | Inter | 14px | 300 | 0.01em | none |
| Data label | Inter | 12px | 500 | 0.06em | uppercase |
| Data value | JetBrains Mono | 16px | 500 | 0 | none |
| Small caption | Inter | 11px | 400 | 0.04em | uppercase |

---

## Color System

### Base Palette

| Token | Hex | Usage |
|-------|-----|-------|
| `--bg-primary` | `#FAFAFA` | Page background |
| `--bg-secondary` | `#F0F0F0` | Card backgrounds, elevated surfaces |
| `--bg-dark` | `#1A1A1A` | Sidebar, footer, inverted sections |
| `--text-primary` | `#1A1A1A` | Headlines, primary text |
| `--text-secondary` | `#5A5A5A` | Body text, descriptions |
| `--text-tertiary` | `#8A8A8A` | Captions, labels, timestamps |
| `--text-on-dark` | `#FAFAFA` | Text on dark backgrounds |
| `--border` | `#E0E0E0` | Dividers, card borders |
| `--border-subtle` | `#EEEEEE` | Subtle separators |

### Signal Colors (Succession-inspired subtle shifts)

These are understated — not neon, not screaming. Think muted, tasteful tones that shift meaning without overwhelming.

| Token | Hex | Usage |
|-------|-----|-------|
| `--signal-bearish` | `#8B4513` | PUT signals — warm sienna brown |
| `--signal-bearish-bg` | `#FAF5F0` | PUT signal card background |
| `--signal-bullish` | `#2E5A3E` | CALL signals — deep forest green |
| `--signal-bullish-bg` | `#F0F5F2` | CALL signal card background |
| `--signal-hedge` | `#4A4A6A` | HEDGE signals — muted slate blue |
| `--signal-hedge-bg` | `#F2F2F6` | HEDGE signal card background |
| `--signal-volatility` | `#6A4A6A` | VOLATILITY signals — muted plum |
| `--signal-volatility-bg` | `#F5F2F5` | VOLATILITY signal card background |

### Strength Indicators

Signal strength shifts the text color intensity, not the background:

| Strength | Opacity on signal color |
|----------|------------------------|
| WEAK | 40% |
| MODERATE | 60% |
| STRONG | 80% |
| VERY_STRONG | 100% |
| EXTREME | 100% + underline |

### Semantic Colors

| Token | Hex | Usage |
|-------|-----|-------|
| `--positive` | `#2E5A3E` | Positive change, wins |
| `--negative` | `#8B3A3A` | Negative change, losses |
| `--neutral` | `#5A5A5A` | Unchanged, pending |

---

## Grid System

### Layout Structure

```
┌─────────────────────────────────────────────────────┐
│  max-width: 1200px, centered                        │
│  padding: 48px horizontal, 32px vertical            │
│                                                     │
│  12-column grid, 24px gutter                        │
│                                                     │
│  ┌─────────────────────────────────────────────┐    │
│  │  Full width: cols 1-12                       │    │
│  │  (page title, market strip)                  │    │
│  └─────────────────────────────────────────────┘    │
│                                                     │
│  ┌──────────────┐  ┌──────────────────────────┐    │
│  │  cols 1-4     │  │  cols 5-12               │    │
│  │  (sidebar     │  │  (main content)          │    │
│  │   info)       │  │                          │    │
│  └──────────────┘  └──────────────────────────┘    │
│                                                     │
│  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐      │
│  │ 3-col  │ │ 3-col  │ │ 3-col  │ │ 3-col  │      │
│  │ metric │ │ metric │ │ metric │ │ metric │      │
│  └────────┘ └────────┘ └────────┘ └────────┘      │
│                                                     │
│  Signal cards: full width, stacked vertically       │
│  with 24px gap between cards                        │
└─────────────────────────────────────────────────────┘
```

### Spacing Scale

| Token | Value | Usage |
|-------|-------|-------|
| `--space-xs` | 4px | Inline padding, tight gaps |
| `--space-sm` | 8px | Between related items |
| `--space-md` | 16px | Card internal padding |
| `--space-lg` | 24px | Between cards, grid gutter |
| `--space-xl` | 32px | Section spacing |
| `--space-2xl` | 48px | Major section breaks |
| `--space-3xl` | 64px | Page-level vertical rhythm |

---

## Component Patterns

### Signal Card

```
┌────────────────────────────────────────────────────┐
│  PUT OPPORTUNITY              AAPL         $183.41 │  ← Bebas Neue, signal color
│                                                    │
│  This stock has been climbing fast — its momentum  │  ← Inter 300, always visible
│  score hit 74, which means buyers have been        │     "What's happening" summary
│  aggressive. Historically, prices this stretched   │
│  tend to pull back.                                │
│                                                    │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────┐ │
│  │ STRIKE   │ │ STOP     │ │ TARGET   │ │ R/R  │ │  ← Data grid
│  │ $182.50  │ │ $192.50  │ │ $182.50  │ │ 1:3  │ │     JetBrains Mono
│  └──────────┘ └──────────┘ └──────────┘ └──────┘ │
│                                                    │
│  IV RANK: 62 — Options pricier than usual          │  ← Surfaced metric
│                                                    │
│  ▸ Why this strike price?                          │  ← Expanders (Inter 400)
│  ▸ Options breakdown                               │
│  ▸ Signal strength (4/7)                           │
│                                                    │
│  Risk: Strong earnings could push price higher     │  ← Risk note, Inter 300 italic
│  despite overbought signals. Stop loss: $192.50    │
└────────────────────────────────────────────────────┘
```

Border: 1px `--border`, with left border 3px in signal color.
Background: signal-type-specific subtle tint.

### Metric Tile

```
┌─────────────────┐
│  SYMBOLS SCANNED │  ← Inter 500, 11px, uppercase, --text-tertiary
│                  │
│  47              │  ← JetBrains Mono 500, 32px, --text-primary
└─────────────────┘
```

No animated counters. No glow. Just the number, bold and clear.

### Expander (Learn More)

```
▸ Why this strike price?
─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─
  We picked $182.50 because it gives     ← Inter 300, 14px
  a delta of -0.30 — for every $1 AAPL   ← --text-secondary
  drops, your put gains ~$0.30.           ← indented, with subtle
                                             left border
```

### Screener Table

Clean, minimal table. No colored backgrounds on rows.
- Header: Inter 500, 11px, uppercase, --text-tertiary
- Values: JetBrains Mono 400, 14px
- RSI color: --signal-bearish if >70, --signal-bullish if <30
- Alternating row background: transparent / --bg-secondary

---

## Streamlit Theme Config

```toml
[theme]
base = "light"
primaryColor = "#1A1A1A"
backgroundColor = "#FAFAFA"
secondaryBackgroundColor = "#F0F0F0"
textColor = "#1A1A1A"
font = "sans serif"
```

---

## What This Replaces

Everything from the old terminal aesthetic is removed:
- ❌ Matrix rain animation
- ❌ Scanline overlay
- ❌ Green-on-black color scheme
- ❌ JetBrains Mono as primary font
- ❌ Animated counters with jitter
- ❌ Neon glow effects
- ❌ CRT/hacker styling
- ❌ OLED black background

---

## File Reference

| File | Role |
|------|------|
| `nasdaq_scanner/dashboard.py` | All UI code — CSS + Streamlit components |
| `.streamlit/config.toml` | Streamlit theme base config |
| `docs/DESIGN_SYSTEM.md` | This file — the source of truth |
| `nasdaq_scanner/explanations.py` | Educational text generation |
