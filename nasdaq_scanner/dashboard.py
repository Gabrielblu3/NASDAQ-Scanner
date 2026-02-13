#!/usr/bin/env python3
"""NASDAQ Volatility Scanner - Matrix Terminal Dashboard"""

import sys
from datetime import datetime, timedelta
from pathlib import Path

import streamlit as st
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

from nasdaq_scanner.config.settings import Settings, NASDAQ_100
from nasdaq_scanner.scanner.stock_screener import StockScreener
from nasdaq_scanner.scanner.signal_generator import SignalGenerator, SignalType, SignalStrength
from nasdaq_scanner.tracker.prediction_tracker import PredictionTracker, PredictionStatus

# Page config
st.set_page_config(
    page_title="NASDAQ VOLATILITY TERMINAL",
    page_icon="",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Matrix Theme CSS with falling code animation
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;500;600;700&family=Inter:wght@300;400;500;600;700&display=swap');

    /* Glitch Animation - GPU accelerated, smooth */
    @keyframes glitch {
        0%, 60%, 100% {
            text-shadow: 0 0 10px rgba(0, 255, 65, 0.5);
            transform: translate3d(0, 0, 0);
        }
        62% {
            text-shadow: -2px 0 var(--accent), 2px 0 var(--negative), 0 0 10px rgba(0, 255, 65, 0.5);
            transform: translate3d(1px, 0, 0);
        }
        65% {
            text-shadow: 2px 0 var(--accent), -2px 0 var(--negative), 0 0 10px rgba(0, 255, 65, 0.5);
            transform: translate3d(-1px, 0, 0);
        }
        68% {
            text-shadow: -1px 0 var(--accent), 1px 0 var(--negative), 0 0 10px rgba(0, 255, 65, 0.5);
            transform: translate3d(0, 1px, 0);
        }
        71% {
            text-shadow: 1px 0 var(--accent), -1px 0 var(--negative), 0 0 10px rgba(0, 255, 65, 0.5);
            transform: translate3d(0, -1px, 0);
        }
        74% {
            text-shadow: 0 0 10px rgba(0, 255, 65, 0.5);
            transform: translate3d(0, 0, 0);
        }
    }

    /* Matrix Rain - GPU accelerated for 60fps */
    @keyframes rain-fall {
        0% {
            transform: translate3d(0, -100%, 0);
            opacity: 0;
        }
        5% {
            opacity: 1;
        }
        80% {
            opacity: 0.3;
        }
        100% {
            transform: translate3d(0, 2000px, 0);
            opacity: 0;
        }
    }

    .matrix-rain-container {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        pointer-events: none;
        z-index: 0;
        overflow: hidden;
        contain: strict;
        mask-image: linear-gradient(to bottom,
            rgba(0,0,0,0.4) 0%,
            rgba(0,0,0,0.15) 30%,
            rgba(0,0,0,0.05) 60%,
            rgba(0,0,0,0) 100%);
        -webkit-mask-image: linear-gradient(to bottom,
            rgba(0,0,0,0.4) 0%,
            rgba(0,0,0,0.15) 30%,
            rgba(0,0,0,0.05) 60%,
            rgba(0,0,0,0) 100%);
    }

    .rain-column {
        position: absolute;
        top: -200px;
        color: #00ff41;
        font-family: 'JetBrains Mono', 'Courier New', monospace;
        font-size: 16px;
        line-height: 1.2;
        opacity: 0.20;
        animation: rain-fall linear infinite;
        white-space: pre;
        letter-spacing: 2px;
        text-shadow: 0 0 10px #00ff41, 0 0 20px #00ff41;
        will-change: transform, opacity;
        backface-visibility: hidden;
        -webkit-font-smoothing: antialiased;
    }

    .rain-column:nth-child(odd) {
        opacity: 0.12;
        font-size: 14px;
        color: #00dd38;
    }

    .rain-column:nth-child(3n) {
        opacity: 0.25;
        text-shadow: 0 0 15px #00ff41, 0 0 30px #00ff41;
        color: #00ff50;
    }

    .rain-column:nth-child(5n) {
        opacity: 0.30;
        font-size: 18px;
        color: #33ff66;
        text-shadow: 0 0 20px #00ff41, 0 0 40px #00ff41;
    }

    @keyframes blink {
        0%, 49% { opacity: 1; }
        50%, 100% { opacity: 0; }
    }

    /* Root variables */
    :root {
        --matrix-green: #00ff41;
        --matrix-green-dim: #00cc33;
        --matrix-green-dark: #003300;
        --oled-black: #000000;
        --surface: #0a0a0a;
        --surface-elevated: #111111;
        --accent: #00ffff;
        --text-primary: #ffffff;
        --text-secondary: #00ff41;
        --text-dim: #555555;
        --border: #1a1a1a;
        --negative: #ff0040;
        --positive: #00ff41;
        --warning: #ffaa00;
    }

    /* Global styles */
    * {
        -webkit-font-smoothing: antialiased;
        -moz-osx-font-smoothing: grayscale;
    }

    html {
        scroll-behavior: smooth;
    }

    .stApp {
        background-color: var(--oled-black) !important;
    }

    .main .block-container {
        background-color: var(--oled-black);
        padding: 2rem 3rem;
        max-width: 1400px;
        position: relative;
        z-index: 1;
    }


    /* Typography */
    h1, h2, h3, h4, h5, h6, p, span, div, label {
        font-family: 'Inter', -apple-system, sans-serif !important;
        color: var(--text-primary) !important;
    }

    .mono {
        font-family: 'JetBrains Mono', monospace !important;
    }

    /* Header */
    .terminal-header {
        border-bottom: 1px solid var(--matrix-green);
        padding-bottom: 24px;
        margin-bottom: 32px;
    }

    .terminal-title {
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 28px;
        font-weight: 700;
        letter-spacing: 6px;
        color: var(--matrix-green) !important;
        text-transform: uppercase;
        margin: 0;
        position: relative;
        text-shadow: 0 0 10px rgba(0, 255, 65, 0.5);
        animation: glitch 10s cubic-bezier(0.25, 0.46, 0.45, 0.94) infinite;
        will-change: transform, text-shadow;
        backface-visibility: hidden;
        -webkit-font-smoothing: antialiased;
    }

    /* Hide Streamlit anchor links */
    .stMarkdown a[href^="#"],
    h1 a, h2 a, h3 a, h4 a, h5 a, h6 a,
    [data-testid="stHeaderActionElements"] {
        display: none !important;
    }

    .terminal-subtitle {
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 11px;
        color: var(--text-dim) !important;
        letter-spacing: 3px;
        margin-top: 8px;
    }

    .terminal-time {
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 13px;
        color: var(--matrix-green) !important;
    }

    .cursor-blink::after {
        content: '_';
        animation: blink 1s step-end infinite;
    }

    /* Metrics grid */
    .metric-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 16px;
        margin-bottom: 32px;
    }

    .metric-card {
        background: var(--surface);
        border: 1px solid var(--border);
        border-left: 3px solid var(--matrix-green);
        padding: 20px 24px;
    }

    .metric-label {
        font-family: 'Inter', sans-serif !important;
        font-size: 10px;
        font-weight: 500;
        letter-spacing: 1.5px;
        text-transform: uppercase;
        color: var(--text-dim) !important;
        margin-bottom: 8px;
    }

    .metric-value {
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 32px;
        font-weight: 600;
        color: var(--matrix-green) !important;
    }

    /* Signal cards */
    .signal-card {
        background: var(--surface);
        border: 1px solid var(--border);
        margin-bottom: 24px;
        position: relative;
        overflow: hidden;
    }

    .signal-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        width: 4px;
        height: 100%;
    }

    .signal-card.put::before { background: var(--negative); }
    .signal-card.call::before { background: var(--positive); }
    .signal-card.hedge::before { background: var(--warning); }

    .signal-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 20px 24px;
        border-bottom: 1px solid var(--border);
    }

    .signal-type {
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 10px;
        font-weight: 700;
        letter-spacing: 2px;
        padding: 6px 14px;
        text-transform: uppercase;
    }

    .signal-type.put { background: var(--negative); color: var(--oled-black); }
    .signal-type.call { background: var(--positive); color: var(--oled-black); }
    .signal-type.hedge { background: var(--warning); color: var(--oled-black); }

    .signal-symbol {
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 28px;
        font-weight: 700;
        color: var(--text-primary) !important;
        letter-spacing: 3px;
    }

    .signal-strength {
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 11px;
        color: var(--matrix-green) !important;
        letter-spacing: 1px;
    }

    .signal-body {
        padding: 24px;
    }

    .signal-grid {
        display: grid;
        grid-template-columns: repeat(5, 1fr);
        gap: 24px;
        margin-bottom: 24px;
    }

    .signal-metric {
        text-align: left;
    }

    .signal-metric-label {
        font-size: 9px;
        font-weight: 600;
        letter-spacing: 1.5px;
        text-transform: uppercase;
        color: var(--text-dim) !important;
        margin-bottom: 6px;
    }

    .signal-metric-value {
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 20px;
        font-weight: 600;
        color: var(--text-primary) !important;
    }

    .signal-metric-value.positive { color: var(--positive) !important; }
    .signal-metric-value.negative { color: var(--negative) !important; }
    .signal-metric-value.accent { color: var(--accent) !important; }

    /* Timing section - THE KEY FEATURE */
    .timing-box {
        background: linear-gradient(135deg, var(--surface-elevated) 0%, #0d1a0d 100%);
        border: 2px solid var(--matrix-green);
        padding: 20px 24px;
        margin-top: 20px;
        position: relative;
    }

    .timing-box::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 1px;
        background: linear-gradient(90deg, transparent, var(--matrix-green), transparent);
    }

    .timing-label {
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 9px;
        font-weight: 700;
        letter-spacing: 3px;
        text-transform: uppercase;
        color: var(--matrix-green) !important;
        margin-bottom: 12px;
    }

    .timing-value {
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 22px;
        font-weight: 600;
        color: var(--text-primary) !important;
        letter-spacing: 1px;
    }

    .timing-countdown {
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 13px;
        color: var(--accent) !important;
        margin-top: 8px;
    }

    .timing-note {
        font-size: 11px;
        color: var(--text-dim) !important;
        margin-top: 12px;
        line-height: 1.5;
    }

    /* Rationale */
    .signal-rationale {
        font-size: 12px;
        color: var(--text-dim) !important;
        line-height: 1.7;
        padding-top: 20px;
        border-top: 1px solid var(--border);
        letter-spacing: 0.3px;
    }

    /* Data table */
    .data-table {
        width: 100%;
        border-collapse: collapse;
        font-family: 'JetBrains Mono', monospace;
        font-size: 12px;
    }

    .data-table th {
        text-align: left;
        padding: 14px 16px;
        font-size: 9px;
        font-weight: 700;
        letter-spacing: 1.5px;
        text-transform: uppercase;
        color: var(--text-dim) !important;
        border-bottom: 1px solid var(--matrix-green);
        background: var(--surface);
    }

    .data-table td {
        padding: 14px 16px;
        border-bottom: 1px solid var(--border);
        color: var(--text-primary) !important;
    }

    .data-table tr {
        transition: background 0.15s ease;
    }

    .data-table tr:hover td {
        background: var(--surface-elevated);
    }

    .data-table td.positive { color: var(--positive) !important; }
    .data-table td.negative { color: var(--negative) !important; }

    /* Status indicators */
    .status-dot {
        display: inline-block;
        width: 8px;
        height: 8px;
        border-radius: 50%;
        margin-right: 8px;
    }

    @keyframes status-pulse {
        0%, 100% {
            box-shadow: 0 0 4px var(--positive);
            transform: scale(1);
        }
        50% {
            box-shadow: 0 0 12px var(--positive), 0 0 20px var(--positive);
            transform: scale(1.1);
        }
    }

    .status-dot.active {
        background: var(--positive);
        box-shadow: 0 0 8px var(--positive);
        animation: status-pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
        will-change: box-shadow, transform;
    }

    /* Buttons - smooth transitions */
    .stButton > button {
        background: transparent !important;
        border: 1px solid var(--matrix-green) !important;
        color: var(--matrix-green) !important;
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 11px !important;
        font-weight: 600 !important;
        letter-spacing: 2px !important;
        text-transform: uppercase !important;
        padding: 12px 32px !important;
        transition: background 0.3s cubic-bezier(0.4, 0, 0.2, 1),
                    color 0.3s cubic-bezier(0.4, 0, 0.2, 1),
                    box-shadow 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
        will-change: background, color, box-shadow;
    }

    .stButton > button:hover {
        background: var(--matrix-green) !important;
        color: var(--oled-black) !important;
        box-shadow: 0 0 30px var(--matrix-green) !important;
    }

    /* Select box */
    .stSelectbox > div > div {
        background: var(--surface) !important;
        border: 1px solid var(--border) !important;
        color: var(--text-primary) !important;
        font-family: 'JetBrains Mono', monospace !important;
    }

    /* Hide streamlit branding */
    #MainMenu, footer, header { visibility: hidden; }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        background: transparent;
        border-bottom: 1px solid var(--border);
        gap: 0;
    }

    .stTabs [data-baseweb="tab"] {
        background: transparent !important;
        border: none !important;
        color: var(--text-dim) !important;
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 11px !important;
        font-weight: 600 !important;
        letter-spacing: 2px !important;
        text-transform: uppercase !important;
        padding: 16px 32px !important;
    }

    .stTabs [aria-selected="true"] {
        color: var(--matrix-green) !important;
        border-bottom: 2px solid var(--matrix-green) !important;
    }

    /* Section dividers */
    .section-divider {
        height: 1px;
        background: linear-gradient(90deg, transparent, var(--matrix-green-dim), transparent);
        margin: 40px 0;
        opacity: 0.5;
    }

    /* Action box */
    .action-box {
        background: var(--surface);
        border: 1px solid var(--accent);
        padding: 16px 20px;
        margin-top: 16px;
    }

    .action-label {
        font-size: 9px;
        font-weight: 700;
        letter-spacing: 2px;
        text-transform: uppercase;
        color: var(--accent) !important;
        margin-bottom: 8px;
    }

    .action-text {
        font-size: 13px;
        color: var(--text-primary) !important;
        line-height: 1.5;
    }

    /* PRIMARY SIGNAL PANEL - Hero Section */
    .hero-panel {
        background: linear-gradient(180deg, #001a00 0%, var(--oled-black) 100%);
        border: 1px solid var(--matrix-green);
        padding: 0;
        margin-bottom: 32px;
        position: relative;
        overflow: hidden;
    }

    .hero-panel::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 2px;
        background: var(--matrix-green);
        box-shadow: 0 0 20px var(--matrix-green), 0 0 40px var(--matrix-green);
    }

    .hero-label {
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 9px;
        font-weight: 700;
        letter-spacing: 4px;
        color: var(--matrix-green) !important;
        padding: 16px 24px 8px 24px;
        border-bottom: 1px solid var(--border);
        background: rgba(0, 255, 65, 0.03);
    }

    .hero-content {
        display: grid;
        grid-template-columns: 1fr 1fr 1fr;
        gap: 0;
    }

    .hero-main {
        padding: 24px 32px;
        border-right: 1px solid var(--border);
    }

    .hero-signal-type {
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 2px;
        padding: 4px 12px;
        display: inline-block;
        margin-bottom: 12px;
    }

    .hero-signal-type.put { background: var(--negative); color: var(--oled-black); }
    .hero-signal-type.call { background: var(--positive); color: var(--oled-black); }
    .hero-signal-type.hedge { background: var(--warning); color: var(--oled-black); }

    .hero-symbol {
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 48px;
        font-weight: 700;
        color: var(--text-primary) !important;
        letter-spacing: 4px;
        line-height: 1;
    }

    .hero-price {
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 20px;
        color: var(--text-dim) !important;
        margin-top: 8px;
    }

    .hero-center {
        padding: 24px 32px;
        border-right: 1px solid var(--border);
        display: flex;
        flex-direction: column;
        justify-content: center;
    }

    .hero-timing-label {
        font-size: 9px;
        font-weight: 700;
        letter-spacing: 2px;
        color: var(--matrix-green) !important;
        margin-bottom: 8px;
    }

    .hero-timing-value {
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 24px;
        font-weight: 600;
        color: var(--text-primary) !important;
    }

    .hero-timing-next {
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 12px;
        color: var(--accent) !important;
        margin-top: 8px;
    }

    .hero-right {
        padding: 24px 32px;
        display: flex;
        flex-direction: column;
        justify-content: center;
    }

    .hero-action-label {
        font-size: 9px;
        font-weight: 700;
        letter-spacing: 2px;
        color: var(--accent) !important;
        margin-bottom: 8px;
    }

    .hero-action-text {
        font-size: 13px;
        color: var(--text-primary) !important;
        line-height: 1.6;
    }

    .hero-strike {
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 18px;
        font-weight: 600;
        color: var(--accent) !important;
        margin-top: 12px;
    }

    /* Market Overview Strip */
    .market-strip {
        display: grid;
        grid-template-columns: repeat(6, 1fr);
        gap: 0;
        background: var(--surface);
        border: 1px solid var(--border);
        margin-bottom: 24px;
    }

    .market-strip-item {
        padding: 16px 20px;
        border-right: 1px solid var(--border);
        text-align: center;
    }

    .market-strip-item:last-child {
        border-right: none;
    }

    .market-strip-label {
        font-size: 8px;
        font-weight: 600;
        letter-spacing: 1.5px;
        text-transform: uppercase;
        color: var(--text-dim) !important;
        margin-bottom: 4px;
    }

    .market-strip-value {
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 16px;
        font-weight: 600;
        color: var(--text-primary) !important;
    }

    .market-strip-value.positive { color: var(--positive) !important; }
    .market-strip-value.negative { color: var(--negative) !important; }
    .market-strip-value.warning { color: var(--warning) !important; }
    .market-strip-value.accent { color: var(--accent) !important; }

    /* No signal state */
    .no-signal-hero {
        padding: 40px;
        text-align: center;
    }

    .no-signal-text {
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 14px;
        color: var(--text-dim) !important;
        letter-spacing: 2px;
    }
</style>
""", unsafe_allow_html=True)


def get_optimal_entry_time(signal):
    """Calculate optimal entry time based on signal type and market conditions."""
    now = datetime.now()

    if signal.signal_type == SignalType.PUT_OPPORTUNITY:
        if signal.strength.value >= 4:
            window = "10:00 - 10:30 AM ET"
            rationale = "Enter on morning rally exhaustion. Overbought conditions typically reverse after initial buying pressure fades."
            action = f"Place limit order for {signal.symbol} puts at strike ${signal.suggested_strike:.2f} when underlying reaches ${signal.current_price * 1.005:.2f} or higher."
        else:
            window = "2:30 - 3:00 PM ET"
            rationale = "Enter during afternoon distribution. Institutional profit-taking creates optimal put entry."
            action = f"Place limit order for {signal.symbol} puts at strike ${signal.suggested_strike:.2f}. Target 30-45 DTE expiration."

    elif signal.signal_type == SignalType.CALL_OPPORTUNITY:
        if signal.strength.value >= 4:
            window = "9:45 - 10:15 AM ET"
            rationale = "Enter after opening panic subsides. Oversold bounces typically begin within first 30 minutes."
            action = f"Place limit order for {signal.symbol} calls at strike ${signal.suggested_strike:.2f} when underlying tests ${signal.current_price * 0.995:.2f}."
        else:
            window = "3:00 - 3:30 PM ET"
            rationale = "Enter before power hour. Short covering and momentum buying accelerate into close."
            action = f"Place limit order for {signal.symbol} calls at strike ${signal.suggested_strike:.2f}. Target 30-45 DTE expiration."

    elif signal.signal_type == SignalType.HEDGE_SIGNAL:
        window = "11:30 AM - 1:00 PM ET"
        rationale = "Midday lull provides tightest spreads. Lower volume means better fill prices for protective positions."
        action = f"Buy {signal.symbol} puts at strike ${signal.suggested_strike:.2f} for portfolio protection. Consider 60-90 DTE for time decay buffer."

    else:
        window = "9:35 - 9:45 AM ET"
        rationale = "Capture initial directional momentum before market digests overnight news."
        action = f"Enter {signal.symbol} straddle or strangle at current price level. Expect 3-5% move within 5 sessions."

    # Calculate next occurrence
    next_window = get_next_window_time(now, window)

    return {
        "window": window,
        "rationale": rationale,
        "action": action,
        "next": next_window
    }


def get_next_window_time(now, window):
    """Determine when the next entry window occurs."""
    # Parse window start time
    start_str = window.split(" - ")[0]
    is_pm = "PM" in window
    hour = int(start_str.split(":")[0])
    minute = int(start_str.split(":")[1].split(" ")[0])

    if is_pm and hour != 12:
        hour += 12

    window_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

    # Check if we're on weekend
    if now.weekday() >= 5:
        days_until_monday = 7 - now.weekday()
        next_date = now + timedelta(days=days_until_monday)
        return f"Next: Monday {next_date.strftime('%b %d')} at {start_str}"

    # Check if window has passed today
    if now > window_time:
        if now.weekday() == 4:  # Friday
            next_date = now + timedelta(days=3)
            return f"Next: Monday {next_date.strftime('%b %d')} at {start_str}"
        else:
            next_date = now + timedelta(days=1)
            return f"Next: Tomorrow at {start_str}"

    return f"Next: Today at {start_str}"


def format_strength(strength_value):
    """Format signal strength as visual bar."""
    bars = "=" * strength_value + "-" * (5 - strength_value)
    levels = {5: "EXTREME", 4: "STRONG", 3: "MODERATE", 2: "FAIR", 1: "WEAK"}
    return f"[{bars}] {levels.get(strength_value, '')}"


@st.cache_data(ttl=300)
def run_scan(symbols, include_options=False):
    """Run the scanner and cache results."""
    config = Settings.load()
    config.atr_percentile_min = 50

    screener = StockScreener(config)
    signal_gen = SignalGenerator(config)

    screened = screener.screen_stocks(symbols, include_options_data=include_options)
    signals = signal_gen.generate_signals(screened, max_signals=20)

    return screened, signals


def main():
    # Matrix Rain Background - numbers only
    import random
    rain_columns = ""
    matrix_chars = "0123456789"

    for i in range(60):
        left = i * 1.7
        duration = random.uniform(40, 100)
        delay = random.uniform(0, 50)
        text = "".join([random.choice(matrix_chars) + "\n" for _ in range(50)])
        rain_columns += f'<div class="rain-column" style="left:{left}%;animation-duration:{duration}s;animation-delay:-{delay}s;">{text}</div>'

    st.markdown(f'''<div class="matrix-rain-container">{rain_columns}</div>''', unsafe_allow_html=True)

    # Header
    now = datetime.now()
    market_status = "MARKET OPEN" if (9 <= now.hour < 16 and now.weekday() < 5) else "MARKET CLOSED"

    st.markdown(f"""
    <div class="terminal-header">
        <div style="display: flex; justify-content: space-between; align-items: flex-start;">
            <div>
                <h1 class="terminal-title">VOLATILITY TERMINAL</h1>
                <p class="terminal-subtitle">NASDAQ OPTIONS SIGNAL DETECTION</p>
            </div>
            <div style="text-align: right;">
                <p class="terminal-time">{now.strftime("%Y.%m.%d")}</p>
                <p class="terminal-time cursor-blink">{now.strftime("%H:%M:%S")} ET</p>
                <p class="terminal-subtitle" style="margin-top: 12px;">
                    <span class="status-dot {'active' if 'OPEN' in market_status else ''}"></span>{market_status}
                </p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Controls
    col1, col2, col3 = st.columns([2, 2, 1])

    with col1:
        scan_size = st.selectbox(
            "SCAN UNIVERSE",
            ["TOP 20 NASDAQ", "TOP 50 NASDAQ", "FULL NASDAQ 100"],
            label_visibility="collapsed"
        )

    with col3:
        if st.button("EXECUTE SCAN"):
            st.cache_data.clear()

    # Determine symbols
    if scan_size == "TOP 20 NASDAQ":
        symbols = NASDAQ_100[:20]
    elif scan_size == "TOP 50 NASDAQ":
        symbols = NASDAQ_100[:50]
    else:
        symbols = NASDAQ_100

    # Run scan
    with st.spinner(""):
        try:
            screened, signals = run_scan(symbols)
        except Exception as e:
            st.error(f"SCAN ERROR: {e}")
            return

    # Metrics
    strong_signals = len([s for s in signals if s.strength.value >= 4])

    st.markdown(f"""
    <div class="metric-grid">
        <div class="metric-card">
            <div class="metric-label">Symbols Scanned</div>
            <div class="metric-value">{len(symbols)}</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">Passed Filters</div>
            <div class="metric-value">{len(screened)}</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">Active Signals</div>
            <div class="metric-value">{len(signals)}</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">Strong Signals</div>
            <div class="metric-value">{strong_signals}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # PRIMARY SIGNAL HERO PANEL
    # Find the strongest signal to feature
    put_signals = [s for s in signals if s.signal_type == SignalType.PUT_OPPORTUNITY]
    strong_puts = [s for s in put_signals if s.strength.value >= 4]

    if strong_puts:
        # Sort by RSI (highest = most overbought = best put candidate)
        primary = max(strong_puts, key=lambda s: s.metrics.get('rsi', 0))
        primary_timing = get_optimal_entry_time(primary)

        signal_class = "put"

        st.markdown(f"""
        <div class="hero-panel">
            <div class="hero-label">PRIMARY SIGNAL</div>
            <div class="hero-content">
                <div class="hero-main">
                    <span class="hero-signal-type {signal_class}">{primary.signal_type.value}</span>
                    <div class="hero-symbol">{primary.symbol}</div>
                    <div class="hero-price">${primary.current_price:.2f}</div>
                </div>
                <div class="hero-center">
                    <div class="hero-timing-label">OPTIMAL ENTRY</div>
                    <div class="hero-timing-value">{primary_timing['window']}</div>
                    <div class="hero-timing-next">{primary_timing['next']}</div>
                </div>
                <div class="hero-right">
                    <div class="hero-action-label">ACTION</div>
                    <div class="hero-action-text">Buy puts at strike</div>
                    <div class="hero-strike">${primary.suggested_strike:.2f}</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    elif signals:
        # Show strongest available signal if no strong puts
        primary = max(signals, key=lambda s: s.strength.value)
        primary_timing = get_optimal_entry_time(primary)

        signal_class = {
            SignalType.PUT_OPPORTUNITY: "put",
            SignalType.CALL_OPPORTUNITY: "call",
            SignalType.HEDGE_SIGNAL: "hedge",
            SignalType.VOLATILITY_PLAY: "hedge"
        }.get(primary.signal_type, "hedge")

        action_text = {
            SignalType.PUT_OPPORTUNITY: "Buy puts at strike",
            SignalType.CALL_OPPORTUNITY: "Buy calls at strike",
            SignalType.HEDGE_SIGNAL: "Hedge with puts at",
            SignalType.VOLATILITY_PLAY: "Enter volatility play at"
        }.get(primary.signal_type, "Consider position at")

        st.markdown(f"""
        <div class="hero-panel">
            <div class="hero-label">PRIMARY SIGNAL</div>
            <div class="hero-content">
                <div class="hero-main">
                    <span class="hero-signal-type {signal_class}">{primary.signal_type.value}</span>
                    <div class="hero-symbol">{primary.symbol}</div>
                    <div class="hero-price">${primary.current_price:.2f}</div>
                </div>
                <div class="hero-center">
                    <div class="hero-timing-label">OPTIMAL ENTRY</div>
                    <div class="hero-timing-value">{primary_timing['window']}</div>
                    <div class="hero-timing-next">{primary_timing['next']}</div>
                </div>
                <div class="hero-right">
                    <div class="hero-action-label">ACTION</div>
                    <div class="hero-action-text">{action_text}</div>
                    <div class="hero-strike">${primary.suggested_strike:.2f}</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="hero-panel">
            <div class="hero-label">PRIMARY SIGNAL</div>
            <div class="no-signal-hero">
                <div class="no-signal-text">SCANNING FOR OPPORTUNITIES...</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # MARKET OVERVIEW STRIP
    # Calculate aggregate metrics
    avg_rsi = sum(s.rsi for s in screened) / len(screened) if screened else 0
    overbought_count = len([s for s in screened if s.rsi > 70])
    oversold_count = len([s for s in screened if s.rsi < 30])
    high_vol_count = len([s for s in screened if s.volatility_regime in ['HIGH', 'EXTREME']])
    put_count = len([s for s in signals if s.signal_type == SignalType.PUT_OPPORTUNITY])
    call_count = len([s for s in signals if s.signal_type == SignalType.CALL_OPPORTUNITY])

    rsi_class = "negative" if avg_rsi > 60 else "positive" if avg_rsi < 40 else ""

    st.markdown(f"""
    <div class="market-strip">
        <div class="market-strip-item">
            <div class="market-strip-label">AVG RSI</div>
            <div class="market-strip-value {rsi_class}">{avg_rsi:.1f}</div>
        </div>
        <div class="market-strip-item">
            <div class="market-strip-label">OVERBOUGHT</div>
            <div class="market-strip-value negative">{overbought_count}</div>
        </div>
        <div class="market-strip-item">
            <div class="market-strip-label">OVERSOLD</div>
            <div class="market-strip-value positive">{oversold_count}</div>
        </div>
        <div class="market-strip-item">
            <div class="market-strip-label">HIGH VOL</div>
            <div class="market-strip-value warning">{high_vol_count}</div>
        </div>
        <div class="market-strip-item">
            <div class="market-strip-label">PUT SIGNALS</div>
            <div class="market-strip-value negative">{put_count}</div>
        </div>
        <div class="market-strip-item">
            <div class="market-strip-label">CALL SIGNALS</div>
            <div class="market-strip-value positive">{call_count}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Tabs
    tab1, tab2, tab3, tab4 = st.tabs(["SIGNALS", "SCREENER", "TRACKER", "DOCUMENTATION"])

    with tab1:
        if not signals:
            st.markdown("""
            <div style="text-align: center; padding: 80px 0; color: #333;">
                <p style="font-family: 'JetBrains Mono', monospace; font-size: 13px; letter-spacing: 3px; color: #444;">
                    NO ACTIONABLE SIGNALS DETECTED
                </p>
                <p style="font-size: 11px; margin-top: 12px; color: #333;">
                    Expand scan universe or wait for market conditions to change
                </p>
            </div>
            """, unsafe_allow_html=True)
        else:
            for signal in signals:
                signal_class = {
                    SignalType.PUT_OPPORTUNITY: "put",
                    SignalType.CALL_OPPORTUNITY: "call",
                    SignalType.HEDGE_SIGNAL: "hedge",
                    SignalType.VOLATILITY_PLAY: "hedge"
                }.get(signal.signal_type, "hedge")

                timing = get_optimal_entry_time(signal)

                # Build metrics - handle None values
                price_str = f"${signal.current_price:.2f}" if signal.current_price else "-"
                strike_str = f"${signal.suggested_strike:.2f}" if signal.suggested_strike else None
                stop_str = f"${signal.stop_loss:.2f}" if signal.stop_loss else None
                target_str = f"${signal.target_price:.2f}" if signal.target_price else None
                rr_str = f"{signal.risk_reward_ratio:.1f}:1" if signal.risk_reward_ratio else None

                # Render signal card with st.container for proper HTML
                signal_html = f'''<div class="signal-card {signal_class}">
                    <div class="signal-header">
                        <div style="display: flex; align-items: center; gap: 20px;">
                            <span class="signal-type {signal_class}">{signal.signal_type.value}</span>
                            <span class="signal-symbol">{signal.symbol}</span>
                        </div>
                        <div class="signal-strength">{format_strength(signal.strength.value)}</div>
                    </div>
                    <div class="signal-body">
                        <div class="signal-grid">
                            <div class="signal-metric">
                                <div class="signal-metric-label">Current Price</div>
                                <div class="signal-metric-value">{price_str}</div>
                            </div>'''

                if strike_str:
                    signal_html += f'''
                            <div class="signal-metric">
                                <div class="signal-metric-label">Strike Price</div>
                                <div class="signal-metric-value accent">{strike_str}</div>
                            </div>'''

                if stop_str:
                    signal_html += f'''
                            <div class="signal-metric">
                                <div class="signal-metric-label">Stop Loss</div>
                                <div class="signal-metric-value negative">{stop_str}</div>
                            </div>'''

                if target_str:
                    signal_html += f'''
                            <div class="signal-metric">
                                <div class="signal-metric-label">Target Price</div>
                                <div class="signal-metric-value positive">{target_str}</div>
                            </div>'''

                if rr_str:
                    signal_html += f'''
                            <div class="signal-metric">
                                <div class="signal-metric-label">Risk/Reward</div>
                                <div class="signal-metric-value">{rr_str}</div>
                            </div>'''

                signal_html += f'''
                        </div>
                        <div class="timing-box">
                            <div class="timing-label">OPTIMAL ENTRY WINDOW</div>
                            <div class="timing-value">{timing['window']}</div>
                            <div class="timing-countdown">{timing['next']}</div>
                            <div class="timing-note">{timing['rationale']}</div>
                        </div>
                        <div class="action-box">
                            <div class="action-label">RECOMMENDED ACTION</div>
                            <div class="action-text">{timing['action']}</div>
                        </div>
                        <div class="signal-rationale">
                            <strong style="color: #555;">SIGNAL BASIS:</strong> {signal.rationale}
                        </div>
                    </div>
                </div>'''

                st.markdown(signal_html, unsafe_allow_html=True)

    with tab2:
        if not screened:
            st.markdown("""
            <div style="text-align: center; padding: 80px 0; color: #333;">
                <p style="font-family: 'JetBrains Mono', monospace;">NO DATA</p>
            </div>
            """, unsafe_allow_html=True)
        else:
            table_rows = ""
            for s in screened:
                rsi_val = s.rsi if s.rsi else 0
                rsi_class = "negative" if rsi_val > 70 else "positive" if rsi_val < 30 else ""
                change_val = s.change_pct if s.change_pct else 0
                change_class = "positive" if change_val > 0 else "negative" if change_val < 0 else ""
                price_str = f"${s.current_price:.2f}" if s.current_price else "-"
                atr_str = f"{s.atr_percentile:.0f}%" if s.atr_percentile else "-"
                hv_str = f"{s.historical_volatility*100:.1f}%" if s.historical_volatility else "-"
                regime_str = s.volatility_regime if s.volatility_regime else "-"

                table_rows += f'''<tr>
                    <td style="font-weight: 600;">{s.symbol}</td>
                    <td>{price_str}</td>
                    <td class="{change_class}">{change_val:+.2f}%</td>
                    <td class="{rsi_class}">{rsi_val:.1f}</td>
                    <td>{atr_str}</td>
                    <td>{hv_str}</td>
                    <td style="text-transform: uppercase; font-size: 10px; letter-spacing: 1px;">{regime_str}</td>
                </tr>'''

            st.markdown(f"""
            <table class="data-table">
                <thead>
                    <tr>
                        <th>Symbol</th>
                        <th>Price</th>
                        <th>Change</th>
                        <th>RSI</th>
                        <th>ATR Percentile</th>
                        <th>Historical Vol</th>
                        <th>Regime</th>
                    </tr>
                </thead>
                <tbody>
                    {table_rows}
                </tbody>
            </table>
            """, unsafe_allow_html=True)

    with tab3:
        # TRACKER TAB - Prediction Performance
        tracker = PredictionTracker()

        # Save current signals to tracker (if not already saved)
        for signal in signals:
            if not tracker.check_duplicate(signal.symbol, signal.signal_type.value, hours=24):
                tracker.record_signal(
                    symbol=signal.symbol,
                    signal_type=signal.signal_type.value,
                    signal_strength=signal.strength.value,
                    entry_price=signal.current_price,
                    suggested_strike=signal.suggested_strike,
                    target_price=signal.target_price,
                    stop_loss=signal.stop_loss,
                    expiry_days=30
                )

        # Update pending predictions with current prices
        price_data = {s.symbol: s.current_price for s in screened}
        tracker.check_and_update_predictions(price_data)
        tracker.expire_old_predictions()

        # Get statistics
        stats = tracker.get_statistics()

        # Stats header
        st.markdown(f"""
        <h3 style="font-family: 'JetBrains Mono', monospace; font-size: 14px; color: #00ff41 !important;
                   letter-spacing: 3px; margin: 0 0 24px 0; font-weight: 600;">
            PREDICTION PERFORMANCE
        </h3>

        <div class="metric-grid">
            <div class="metric-card">
                <div class="metric-label">Total Predictions</div>
                <div class="metric-value">{stats['total_predictions']}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Win Rate</div>
                <div class="metric-value" style="color: {'#00ff41' if stats['win_rate'] >= 50 else '#ff0040'} !important;">{stats['win_rate']:.1f}%</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Wins / Losses</div>
                <div class="metric-value"><span style="color: #00ff41;">{stats['wins']}</span> / <span style="color: #ff0040;">{stats['losses']}</span></div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Pending</div>
                <div class="metric-value" style="color: #00ffff !important;">{stats['pending']}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Detailed stats
        st.markdown(f"""
        <div class="metric-grid" style="margin-top: 16px;">
            <div class="metric-card">
                <div class="metric-label">Avg Win</div>
                <div class="metric-value positive">+{stats['avg_win_pct']:.1f}%</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Avg Loss</div>
                <div class="metric-value negative">{stats['avg_loss_pct']:.1f}%</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Profit Factor</div>
                <div class="metric-value">{stats['profit_factor']:.2f}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Last 30 Days</div>
                <div class="metric-value">{stats['recent_30d']['win_rate']:.0f}%</div>
            </div>
        </div>

        <div class="section-divider"></div>
        """, unsafe_allow_html=True)

        # Performance by signal type
        if stats['by_signal_type']:
            st.markdown("""
            <h3 style="font-family: 'JetBrains Mono', monospace; font-size: 12px; color: #00ff41 !important;
                       letter-spacing: 2px; margin: 24px 0 16px 0; font-weight: 600;">
                BY SIGNAL TYPE
            </h3>
            """, unsafe_allow_html=True)

            type_rows = ""
            for sig_type, data in stats['by_signal_type'].items():
                color = "#ff0040" if "PUT" in sig_type else "#00ff41" if "CALL" in sig_type else "#ffaa00"
                type_rows += f"""
                <tr>
                    <td style="color: {color}; font-weight: 600;">{sig_type}</td>
                    <td>{data['total']}</td>
                    <td class="positive">{data['wins']}</td>
                    <td class="negative">{data['losses']}</td>
                    <td style="color: {'#00ff41' if data['win_rate'] >= 50 else '#ff0040'};">{data['win_rate']:.1f}%</td>
                </tr>
                """

            st.markdown(f"""
            <table class="data-table">
                <thead>
                    <tr>
                        <th>Signal Type</th>
                        <th>Total</th>
                        <th>Wins</th>
                        <th>Losses</th>
                        <th>Win Rate</th>
                    </tr>
                </thead>
                <tbody>
                    {type_rows}
                </tbody>
            </table>
            """, unsafe_allow_html=True)

        st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

        # Recent predictions table
        st.markdown("""
        <h3 style="font-family: 'JetBrains Mono', monospace; font-size: 12px; color: #00ff41 !important;
                   letter-spacing: 2px; margin: 24px 0 16px 0; font-weight: 600;">
            RECENT PREDICTIONS
        </h3>
        """, unsafe_allow_html=True)

        predictions = tracker.get_predictions(limit=20)

        if predictions:
            pred_rows = ""
            for pred in predictions:
                status_color = {
                    PredictionStatus.WIN: "#00ff41",
                    PredictionStatus.LOSS: "#ff0040",
                    PredictionStatus.PENDING: "#00ffff",
                    PredictionStatus.EXPIRED: "#555555",
                    PredictionStatus.CANCELLED: "#555555"
                }.get(pred.status, "#ffffff")

                signal_color = "#ff0040" if "PUT" in pred.signal_type else "#00ff41" if "CALL" in pred.signal_type else "#ffaa00"

                profit_display = f"{pred.profit_pct:+.1f}%" if pred.profit_pct is not None else "-"
                profit_class = "positive" if pred.profit_pct and pred.profit_pct > 0 else "negative" if pred.profit_pct and pred.profit_pct < 0 else ""

                outcome_display = f"${pred.outcome_price:.2f}" if pred.outcome_price else "-"
                date_display = pred.created_at.strftime('%m/%d %H:%M') if pred.created_at else '-'

                pred_rows += f"""
                <tr>
                    <td>{date_display}</td>
                    <td style="font-weight: 600;">{pred.symbol}</td>
                    <td style="color: {signal_color};">{pred.signal_type}</td>
                    <td>${pred.entry_price:.2f}</td>
                    <td>{outcome_display}</td>
                    <td class="{profit_class}">{profit_display}</td>
                    <td style="color: {status_color}; text-transform: uppercase;">{pred.status.value}</td>
                </tr>
                """

            st.markdown(f"""
            <table class="data-table">
                <thead>
                    <tr>
                        <th>Date</th>
                        <th>Symbol</th>
                        <th>Type</th>
                        <th>Entry</th>
                        <th>Outcome</th>
                        <th>P/L</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
                    {pred_rows}
                </tbody>
            </table>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style="text-align: center; padding: 40px 0; color: #333;">
                <p style="font-family: 'JetBrains Mono', monospace; font-size: 12px; letter-spacing: 2px; color: #444;">
                    NO PREDICTIONS RECORDED YET
                </p>
                <p style="font-size: 11px; margin-top: 8px; color: #333;">
                    Predictions will appear here as signals are generated
                </p>
            </div>
            """, unsafe_allow_html=True)

        # Manual resolution form
        st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
        st.markdown("""
        <h3 style="font-family: 'JetBrains Mono', monospace; font-size: 12px; color: #00ff41 !important;
                   letter-spacing: 2px; margin: 24px 0 16px 0; font-weight: 600;">
            MANUAL RESOLUTION
        </h3>
        """, unsafe_allow_html=True)

        pending_preds = tracker.get_predictions(status=PredictionStatus.PENDING)
        if pending_preds:
            col1, col2, col3, col4 = st.columns([2, 1, 1, 1])

            with col1:
                pred_options = {f"{p.symbol} - {p.signal_type} (${p.entry_price:.2f})": p.id for p in pending_preds}
                selected = st.selectbox("Select Prediction", list(pred_options.keys()), label_visibility="collapsed")

            with col2:
                outcome_status = st.selectbox("Outcome", ["win", "loss", "expired"], label_visibility="collapsed")

            with col3:
                outcome_price = st.number_input("Exit Price", min_value=0.0, step=0.01, label_visibility="collapsed")

            with col4:
                if st.button("RESOLVE"):
                    if selected and outcome_price > 0:
                        tracker.manually_resolve(
                            pred_options[selected],
                            outcome_status,
                            outcome_price,
                            "Manually resolved"
                        )
                        st.rerun()
        else:
            st.markdown("""
            <p style="font-size: 11px; color: #333;">No pending predictions to resolve.</p>
            """, unsafe_allow_html=True)

    with tab4:
        # Documentation - Signal Types
        doc_signal_types = '''<h3 style="font-family: 'JetBrains Mono', monospace; font-size: 14px; color: #00ff41 !important; letter-spacing: 3px; margin: 32px 0 20px 0; font-weight: 600;">SIGNAL TYPES</h3>
<table class="data-table">
<thead><tr><th>Type</th><th>Trigger Conditions</th><th>Action</th></tr></thead>
<tbody>
<tr><td style="color: #ff0040; font-weight: 600;">PUT</td><td>RSI above 70, price above upper Bollinger Band, elevated ATR</td><td>Buy put options, anticipate mean reversion</td></tr>
<tr><td style="color: #00ff41; font-weight: 600;">CALL</td><td>RSI below 30, price below lower Bollinger Band</td><td>Buy call options, anticipate oversold bounce</td></tr>
<tr><td style="color: #ffaa00; font-weight: 600;">HEDGE</td><td>Volatility regime HIGH or EXTREME, HV rank above 80</td><td>Buy protective puts on existing positions</td></tr>
</tbody>
</table>'''
        st.markdown(doc_signal_types, unsafe_allow_html=True)

        st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

        # Documentation - Entry Timing
        doc_timing = '''<h3 style="font-family: 'JetBrains Mono', monospace; font-size: 14px; color: #00ff41 !important; letter-spacing: 3px; margin: 32px 0 20px 0; font-weight: 600;">ENTRY TIMING METHODOLOGY</h3>
<table class="data-table">
<thead><tr><th>Signal</th><th>Window</th><th>Logic</th></tr></thead>
<tbody>
<tr><td>PUT Strong</td><td>10:00-10:30 AM</td><td>Morning rally exhaustion point</td></tr>
<tr><td>PUT Moderate</td><td>2:30-3:00 PM</td><td>Afternoon distribution phase</td></tr>
<tr><td>CALL Strong</td><td>9:45-10:15 AM</td><td>Post-open panic exhaustion</td></tr>
<tr><td>CALL Moderate</td><td>3:00-3:30 PM</td><td>Pre-close momentum buildup</td></tr>
<tr><td>HEDGE</td><td>11:30 AM-1:00 PM</td><td>Midday lull, tighter spreads</td></tr>
</tbody>
</table>'''
        st.markdown(doc_timing, unsafe_allow_html=True)

        st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

        # Documentation - Indicators
        doc_indicators = '''<h3 style="font-family: 'JetBrains Mono', monospace; font-size: 14px; color: #00ff41 !important; letter-spacing: 3px; margin: 32px 0 20px 0; font-weight: 600;">INDICATOR DEFINITIONS</h3>
<table class="data-table">
<thead><tr><th>Indicator</th><th>Definition</th><th>Signal Threshold</th></tr></thead>
<tbody>
<tr><td>RSI</td><td>14-period Relative Strength Index</td><td>Above 70 overbought / Below 30 oversold</td></tr>
<tr><td>ATR %ile</td><td>Current ATR relative to 100-day range</td><td>Above 70% indicates elevated volatility</td></tr>
<tr><td>Hist Vol</td><td>20-day annualized standard deviation</td><td>Above 40% is high volatility</td></tr>
<tr><td>BB %B</td><td>Price position within Bollinger Bands</td><td>Above 1.0 or below 0.0 triggers signals</td></tr>
</tbody>
</table>'''
        st.markdown(doc_indicators, unsafe_allow_html=True)

        st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

        # Disclaimer
        doc_disclaimer = '''<p style="font-size: 10px; color: #555; letter-spacing: 1px; line-height: 2; margin-top: 40px;">
This terminal provides analytical signals for informational purposes only and does not constitute financial advice. Options trading involves substantial risk of loss. Past performance does not guarantee future results. Conduct independent research and consider consulting a licensed financial advisor before making investment decisions.
</p>'''
        st.markdown(doc_disclaimer, unsafe_allow_html=True)

    # Footer
    st.markdown(f"""
    <div class="section-divider"></div>
    <div style="display: flex; justify-content: space-between; align-items: center; padding: 16px 0;">
        <span style="font-family: 'JetBrains Mono', monospace; font-size: 9px; color: #222; letter-spacing: 2px;">
            VOLATILITY TERMINAL v2.0
        </span>
        <span style="font-family: 'JetBrains Mono', monospace; font-size: 9px; color: #222; letter-spacing: 2px;">
            DATA SOURCE: ALPACA MARKETS API
        </span>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
