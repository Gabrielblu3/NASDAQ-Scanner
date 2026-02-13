
# NASDAQ Volatility Scanner - User Guide

## Overview

The NASDAQ Volatility Scanner is an AI-powered tool that analyzes market data to identify high-probability options trading opportunities. It scans NASDAQ stocks for technical patterns that historically precede significant price moves, then generates actionable trading signals with specific entry timing.

---

## How It Works

### 1. Data Collection

The scanner pulls real-time and historical price data from **Alpaca Markets API**:
- Daily OHLCV (Open, High, Low, Close, Volume) data
- Minimum 14 trading days of history required
- Scans up to 100 NASDAQ stocks per run

### 2. Technical Analysis

For each stock, the scanner calculates:

| Indicator | Calculation | Purpose |
|-----------|-------------|---------|
| **RSI (14)** | 14-period Relative Strength Index | Identifies overbought (>70) and oversold (<30) conditions |
| **ATR (14)** | 14-period Average True Range | Measures price volatility magnitude |
| **ATR Percentile** | Current ATR vs. 100-day range | Identifies when volatility is elevated |
| **Bollinger Bands** | 20-period SMA with 2 std deviations | Identifies price extremes |
| **Historical Volatility** | 20-day annualized standard deviation | Measures recent price fluctuation |
| **Volatility Regime** | Classification based on HV percentile | LOW / NORMAL / HIGH / EXTREME |

### 3. Screening Filters

Stocks must pass these filters to generate signals:
- ATR Percentile > 50% (elevated volatility)
- Sufficient price history (14+ bars)
- Active trading volume

### 4. Signal Generation

The scanner generates four types of signals:

#### PUT_OPPORTUNITY (Red)
**Trigger:** RSI > 70 AND price above upper Bollinger Band
**Thesis:** Stock is overbought and likely to pull back
**Action:** Buy put options to profit from expected decline

#### CALL_OPPORTUNITY (Green)
**Trigger:** RSI < 30 AND price below lower Bollinger Band
**Thesis:** Stock is oversold and likely to bounce
**Action:** Buy call options to profit from expected rally

#### HEDGE_SIGNAL (Orange)
**Trigger:** Volatility regime HIGH or EXTREME AND HV rank > 80
**Thesis:** Increased risk warrants portfolio protection
**Action:** Buy protective puts on existing long positions

#### VOLATILITY_PLAY (Orange)
**Trigger:** Extreme volatility without clear direction
**Thesis:** Large move expected, direction uncertain
**Action:** Consider straddle or strangle strategies

---

## Signal Strength Rating

Each signal receives a strength rating from 1-5:

| Rating | Label | Meaning |
|--------|-------|---------|
| 5 | EXTREME | Multiple strong confirmations, highest conviction |
| 4 | STRONG | Clear setup with good risk/reward |
| 3 | MODERATE | Valid signal but fewer confirmations |
| 2 | FAIR | Marginal setup, proceed with caution |
| 1 | WEAK | Minimal evidence, speculative |

**Strength factors:**
- RSI extremity (how far above 70 or below 30)
- Bollinger Band position (how far outside bands)
- ATR percentile (higher = more volatile = stronger signal)
- Volatility regime alignment

---

## Entry Timing

The scanner recommends specific entry windows based on market microstructure:

### PUT Signals (Strong - Rating 4-5)
**Window:** 10:00 - 10:30 AM ET
**Rationale:** Morning rally exhaustion. After the opening 30 minutes, initial buying pressure fades. Overbought stocks that failed to break higher often reverse here.

### PUT Signals (Moderate - Rating 1-3)
**Window:** 2:30 - 3:00 PM ET
**Rationale:** Afternoon distribution. Institutional profit-taking creates selling pressure. This is when "smart money" reduces positions.

### CALL Signals (Strong - Rating 4-5)
**Window:** 9:45 - 10:15 AM ET
**Rationale:** Post-opening panic exhaustion. Oversold stocks often see their worst prices in the first 15 minutes, then bounce.

### CALL Signals (Moderate - Rating 1-3)
**Window:** 3:00 - 3:30 PM ET
**Rationale:** Power hour momentum. Short covering and momentum buying accelerate into the close.

### HEDGE Signals
**Window:** 11:30 AM - 1:00 PM ET
**Rationale:** Midday lull. Lower volume means tighter bid-ask spreads and better fill prices for protective positions.

---

## Dashboard Sections

### Hero Panel (Top)
Displays the single most actionable signal:
- **Symbol:** The stock ticker
- **Signal Type:** PUT/CALL/HEDGE badge
- **Price:** Current stock price
- **Entry Window:** Recommended time to execute
- **Strike Price:** Suggested option strike

### Market Overview Strip
Aggregate metrics across all scanned stocks:
- **AVG RSI:** Market-wide sentiment (>60 = bearish bias, <40 = bullish bias)
- **OVERBOUGHT:** Count of stocks with RSI > 70
- **OVERSOLD:** Count of stocks with RSI < 30
- **HIGH VOL:** Stocks in elevated volatility regime
- **PUT/CALL SIGNALS:** Signal type distribution

### Signals Tab
Detailed view of each generated signal with:
- Entry, stop loss, and target prices
- Risk/reward ratio
- Signal rationale
- Timing recommendation

### Screener Tab
Raw data table showing all stocks that passed filters:
- Current price and daily change
- RSI, ATR percentile, historical volatility
- Volatility regime classification

### Tracker Tab
Historical performance tracking:
- All past predictions with outcomes
- Win rate and profit statistics
- Pending signals awaiting resolution

---

## Understanding the Output

### Example Signal Interpretation

```
Signal: PUT_OPPORTUNITY
Symbol: BKR
Strength: [=====-] STRONG
Current Price: $56.73
Strike Price: $56.00
RSI: 74.3
Entry Window: 10:00 - 10:30 AM ET
```

**Translation:** Baker Hughes (BKR) is showing overbought conditions with RSI at 74.3 (above 70 threshold). The scanner recommends buying put options at the $56 strike. Enter the position between 10:00-10:30 AM when the morning rally typically exhausts.

---

## Files and Structure

```
NASDAQ_Scanner/
├── nasdaq_scanner/
│   ├── config/settings.py      # Thresholds and API configuration
│   ├── data/
│   │   ├── alpaca_client.py    # Alpaca API connection
│   │   └── market_data.py      # Price data fetching
│   ├── indicators/
│   │   ├── technical.py        # RSI, ATR, Bollinger Bands
│   │   └── volatility.py       # HV, volatility regime
│   ├── scanner/
│   │   ├── stock_screener.py   # Filtering logic
│   │   └── signal_generator.py # Signal creation
│   ├── tracker/
│   │   └── prediction_tracker.py # Performance tracking
│   └── dashboard.py            # Streamlit web interface
├── data/
│   └── predictions.db          # SQLite database for tracking
├── .env                        # API keys (not shared)
├── run_dashboard.command       # Double-click to launch
└── run_scan.command           # Double-click for quick scan
```

---

## Running the Scanner

### Web Dashboard
Double-click `run_dashboard.command` or run:
```bash
cd ~/Desktop/NASDAQ_Scanner
python3 -m streamlit run nasdaq_scanner/dashboard.py
```
Opens at http://localhost:8501

### Command Line Scan
Double-click `run_scan.command` or run:
```bash
cd ~/Desktop/NASDAQ_Scanner
python3 -m nasdaq_scanner.main --once
```

---

## Configuration

Edit `.env` file for API credentials:
```
ALPACA_API_KEY=your_key
ALPACA_SECRET_KEY=your_secret
```

Edit `nasdaq_scanner/config/settings.py` for thresholds:
- `RSI_OVERBOUGHT = 70` (trigger for PUT signals)
- `RSI_OVERSOLD = 30` (trigger for CALL signals)
- `ATR_PERCENTILE_MIN = 50` (minimum volatility filter)

---

## Risk Disclaimer

This scanner provides analytical signals for **informational purposes only** and does not constitute financial advice. Options trading involves substantial risk of loss. Past performance does not guarantee future results.

- Never risk more than you can afford to lose
- Consider paper trading before using real capital
- Conduct independent research before any trade
- Consult a licensed financial advisor for personalized advice

---

## Prediction Tracking

The scanner automatically tracks all generated signals and their outcomes:

1. **Signal Recorded:** When generated, signals are saved with timestamp, price, and targets
2. **Outcome Tracked:** The system checks if price hit target or stop loss
3. **Statistics Calculated:** Win rate, average return, profit factor
4. **Performance Displayed:** View historical accuracy in the Tracker tab

This allows you to evaluate the scanner's effectiveness over time and adjust your confidence in different signal types.
