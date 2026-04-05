#!/usr/bin/env python3
"""NASDAQ Volatility Scanner - Editorial Dashboard with Educational Insights."""

import sys
from datetime import datetime
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

sys.path.insert(0, str(Path(__file__).parent.parent))

from nasdaq_scanner.config.settings import Settings, NASDAQ_100
from nasdaq_scanner.scanner.stock_screener import StockScreener
from nasdaq_scanner.scanner.signal_generator import SignalGenerator, SignalType, SignalStrength
from nasdaq_scanner.tracker.prediction_tracker import PredictionTracker, PredictionStatus
from nasdaq_scanner.explanations import (
    generate_signal_summary,
    generate_strike_explanation,
    format_greeks_educational,
    generate_strength_breakdown,
    generate_market_summary,
    generate_risk_note,
    generate_iv_explanation,
)
from nasdaq_scanner.user_profile import UserProfile

# Page config
st.set_page_config(
    page_title="NASDAQ VOLATILITY SCANNER",
    page_icon="",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# =============================================================================
# EDITORIAL DESIGN SYSTEM CSS
# Inspired by Succession credits + Faction Collective
# Reference: docs/DESIGN_SYSTEM.md
# =============================================================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Inter:wght@300;400;500;600&family=JetBrains+Mono:wght@400;500&display=swap');

    /* =========================================================
       Design Tokens
       ========================================================= */
    :root {
        --bg-primary: #FAFAFA;
        --bg-secondary: #F0F0F0;
        --bg-dark: #1A1A1A;
        --text-primary: #1A1A1A;
        --text-secondary: #5A5A5A;
        --text-tertiary: #8A8A8A;
        --text-on-dark: #FAFAFA;
        --border: #E0E0E0;
        --border-subtle: #EEEEEE;

        /* Signal colors — subtle, Succession-inspired shifts */
        --signal-bearish: #8B4513;
        --signal-bearish-bg: #FAF5F0;
        --signal-bullish: #2E5A3E;
        --signal-bullish-bg: #F0F5F2;
        --signal-hedge: #4A4A6A;
        --signal-hedge-bg: #F2F2F6;
        --signal-volatility: #6A4A6A;
        --signal-volatility-bg: #F5F2F5;

        --positive: #2E5A3E;
        --negative: #8B3A3A;
        --neutral: #5A5A5A;

        /* Spacing */
        --space-xs: 4px;
        --space-sm: 8px;
        --space-md: 16px;
        --space-lg: 24px;
        --space-xl: 32px;
        --space-2xl: 48px;
    }

    /* =========================================================
       Global
       ========================================================= */
    * {
        -webkit-font-smoothing: antialiased;
        -moz-osx-font-smoothing: grayscale;
    }

    .stApp {
        background-color: var(--bg-primary) !important;
    }

    .main .block-container {
        background-color: var(--bg-primary);
        padding: 32px 48px;
        max-width: 1200px;
    }

    /* Hide Streamlit branding */
    #MainMenu, footer, header { visibility: hidden; }

    /* Hide anchor links */
    .stMarkdown a[href^="#"],
    h1 a, h2 a, h3 a,
    [data-testid="stHeaderActionElements"] {
        display: none !important;
    }

    /* =========================================================
       Typography
       ========================================================= */
    /* Text defaults — scoped to avoid breaking Streamlit widget icons */
    h1, h2, h3, h4, h5, h6, p, label {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
        color: var(--text-primary) !important;
    }

    /* Apply to our rendered HTML content, not widget internals */
    .stMarkdown span, .stMarkdown div {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
        color: var(--text-primary) !important;
    }

    .headline {
        font-family: 'Bebas Neue', 'Arial Narrow', sans-serif !important;
        font-weight: 400;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        color: var(--text-primary) !important;
    }

    .headline-lg { font-size: 72px; line-height: 1; }
    .headline-md { font-size: 36px; line-height: 1.1; }
    .headline-sm { font-size: 20px; line-height: 1.2; letter-spacing: 0.06em; }

    .mono {
        font-family: 'JetBrains Mono', 'Consolas', monospace !important;
    }

    .label {
        font-family: 'Inter', sans-serif !important;
        font-size: 11px;
        font-weight: 500;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        color: var(--text-tertiary) !important;
    }

    .body-light {
        font-family: 'Inter', sans-serif !important;
        font-size: 14px;
        font-weight: 300;
        line-height: 1.7;
        color: var(--text-secondary) !important;
    }

    /* =========================================================
       Page Header
       ========================================================= */
    .page-header {
        border-bottom: 1px solid var(--border);
        padding-bottom: var(--space-lg);
        margin-bottom: var(--space-xl);
    }

    .page-header-row {
        display: flex;
        justify-content: space-between;
        align-items: flex-end;
    }

    .market-status {
        font-family: 'Inter', sans-serif !important;
        font-size: 11px;
        font-weight: 500;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        color: var(--text-tertiary) !important;
    }

    .status-dot {
        display: inline-block;
        width: 6px;
        height: 6px;
        border-radius: 50%;
        margin-right: 6px;
        background: var(--text-tertiary);
    }

    .status-dot.active {
        background: var(--positive);
    }

    .time-display {
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 13px;
        color: var(--text-tertiary) !important;
    }

    /* =========================================================
       Metric Cards
       ========================================================= */
    .metric-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: var(--space-lg);
        margin-bottom: var(--space-xl);
    }

    .metric-card {
        background: white;
        border: 1px solid var(--border-subtle);
        padding: 20px 24px;
    }

    .metric-card-label {
        font-family: 'Inter', sans-serif !important;
        font-size: 11px;
        font-weight: 500;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        color: var(--text-tertiary) !important;
        margin-bottom: var(--space-sm);
    }

    .metric-card-value {
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 32px;
        font-weight: 500;
        color: var(--text-primary) !important;
    }

    /* =========================================================
       Hero Signal Panel
       ========================================================= */
    .hero-panel {
        background: white;
        border: 1px solid var(--border);
        border-left: 4px solid var(--text-primary);
        margin-bottom: var(--space-xl);
    }

    .hero-panel.put { border-left-color: var(--signal-bearish); }
    .hero-panel.call { border-left-color: var(--signal-bullish); }
    .hero-panel.hedge { border-left-color: var(--signal-hedge); }
    .hero-panel.volatility { border-left-color: var(--signal-volatility); }

    .hero-label {
        font-family: 'Inter', sans-serif !important;
        font-size: 12px;
        font-weight: 500;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: var(--text-tertiary) !important;
        padding: 16px 24px 8px 24px;
        border-bottom: 1px solid var(--border-subtle);
    }

    .hero-content {
        display: grid;
        grid-template-columns: 1fr 1fr 1fr;
        gap: 0;
    }

    .hero-section {
        padding: 24px 32px;
    }

    .hero-section + .hero-section {
        border-left: 1px solid var(--border-subtle);
    }

    .hero-symbol {
        font-family: 'Bebas Neue', sans-serif !important;
        font-size: 48px;
        letter-spacing: 0.04em;
        color: var(--text-primary) !important;
        line-height: 1;
    }

    .hero-price {
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 18px;
        color: var(--text-secondary) !important;
        margin-top: 4px;
    }

    /* =========================================================
       Signal Cards
       ========================================================= */
    .signal-card {
        background: white;
        border: 1px solid var(--border);
        border-left: 3px solid var(--text-primary);
        margin-bottom: var(--space-lg);
    }

    .signal-card.put { border-left-color: var(--signal-bearish); background: var(--signal-bearish-bg); }
    .signal-card.call { border-left-color: var(--signal-bullish); background: var(--signal-bullish-bg); }
    .signal-card.hedge { border-left-color: var(--signal-hedge); background: var(--signal-hedge-bg); }
    .signal-card.volatility { border-left-color: var(--signal-volatility); background: var(--signal-volatility-bg); }

    .signal-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 20px 24px;
        border-bottom: 1px solid var(--border-subtle);
    }

    .signal-type-badge {
        font-family: 'Bebas Neue', sans-serif !important;
        font-size: 14px;
        letter-spacing: 0.08em;
        padding: 4px 14px;
        text-transform: uppercase;
    }

    .signal-type-badge.put { background: var(--signal-bearish); color: white; }
    .signal-type-badge.call { background: var(--signal-bullish); color: white; }
    .signal-type-badge.hedge { background: var(--signal-hedge); color: white; }
    .signal-type-badge.volatility { background: var(--signal-volatility); color: white; }

    .signal-symbol {
        font-family: 'Bebas Neue', sans-serif !important;
        font-size: 28px;
        letter-spacing: 0.04em;
        color: var(--text-primary) !important;
    }

    .signal-strength-text {
        font-family: 'Inter', sans-serif !important;
        font-size: 11px;
        font-weight: 500;
        letter-spacing: 0.04em;
        color: var(--text-tertiary) !important;
        text-transform: uppercase;
    }

    .signal-body {
        padding: 24px;
    }

    .signal-summary {
        font-family: 'Inter', sans-serif !important;
        font-size: 14px;
        font-weight: 300;
        line-height: 1.7;
        color: var(--text-secondary) !important;
        margin-bottom: 20px;
    }

    .signal-data-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
        gap: var(--space-md);
        margin-bottom: 20px;
    }

    .signal-data-item {}

    .signal-data-label {
        font-family: 'Inter', sans-serif !important;
        font-size: 12px;
        font-weight: 500;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: var(--text-tertiary) !important;
        margin-bottom: 4px;
    }

    .signal-data-value {
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 18px;
        font-weight: 500;
        color: var(--text-primary) !important;
    }

    .signal-data-value.positive { color: var(--positive) !important; }
    .signal-data-value.negative { color: var(--negative) !important; }
    .signal-data-value.accent { color: var(--signal-hedge) !important; }

    /* IV inline explanation */
    .iv-inline {
        font-family: 'Inter', sans-serif !important;
        font-size: 13px;
        font-weight: 300;
        color: var(--text-secondary) !important;
        padding: 12px 16px;
        border-left: 2px solid var(--border);
        margin-bottom: 16px;
        line-height: 1.6;
    }

    /* Risk note */
    .risk-note {
        font-family: 'Inter', sans-serif !important;
        font-size: 13px;
        font-weight: 300;
        font-style: italic;
        color: var(--text-tertiary) !important;
        padding-top: 16px;
        border-top: 1px solid var(--border-subtle);
        line-height: 1.6;
    }

    .risk-note strong {
        font-weight: 500;
        font-style: normal;
        color: var(--negative) !important;
    }

    /* Timing section */
    .timing-section {
        background: white;
        border: 1px solid var(--border-subtle);
        padding: 16px 20px;
        margin-bottom: 16px;
    }

    .timing-label {
        font-family: 'Inter', sans-serif !important;
        font-size: 12px;
        font-weight: 500;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: var(--text-tertiary) !important;
        margin-bottom: 8px;
    }

    .timing-value {
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 18px;
        font-weight: 500;
        color: var(--text-primary) !important;
    }

    .timing-next {
        font-family: 'Inter', sans-serif !important;
        font-size: 12px;
        color: var(--text-tertiary) !important;
        margin-top: 4px;
    }

    .timing-note {
        font-family: 'Inter', sans-serif !important;
        font-size: 13px;
        font-weight: 300;
        color: var(--text-secondary) !important;
        margin-top: 8px;
        line-height: 1.5;
    }

    /* Action section */
    .action-section {
        background: white;
        border: 1px solid var(--border-subtle);
        padding: 16px 20px;
        margin-bottom: 16px;
    }

    .action-label {
        font-family: 'Inter', sans-serif !important;
        font-size: 12px;
        font-weight: 500;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: var(--text-tertiary) !important;
        margin-bottom: 8px;
    }

    .action-text {
        font-family: 'Inter', sans-serif !important;
        font-size: 14px;
        color: var(--text-primary) !important;
        line-height: 1.5;
    }

    /* =========================================================
       Market Overview Strip
       ========================================================= */
    .market-strip {
        display: grid;
        grid-template-columns: repeat(6, 1fr);
        gap: 0;
        background: white;
        border: 1px solid var(--border);
        margin-bottom: var(--space-lg);
    }

    .market-strip-item {
        padding: 16px 20px;
        border-right: 1px solid var(--border-subtle);
        text-align: center;
    }

    .market-strip-item:last-child {
        border-right: none;
    }

    .market-strip-label {
        font-family: 'Inter', sans-serif !important;
        font-size: 12px;
        font-weight: 500;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: var(--text-tertiary) !important;
        margin-bottom: 4px;
    }

    .market-strip-value {
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 16px;
        font-weight: 500;
        color: var(--text-primary) !important;
    }

    .market-strip-value.positive { color: var(--positive) !important; }
    .market-strip-value.negative { color: var(--negative) !important; }
    .market-strip-value.warning { color: var(--signal-hedge) !important; }

    .market-summary {
        font-family: 'Inter', sans-serif !important;
        font-size: 14px;
        font-weight: 300;
        line-height: 1.7;
        color: var(--text-secondary) !important;
        margin-bottom: var(--space-xl);
        padding: 16px 0;
    }

    /* =========================================================
       Data Table
       ========================================================= */
    .data-table {
        width: 100%;
        border-collapse: collapse;
    }

    .data-table th {
        text-align: left;
        padding: 14px 16px;
        font-family: 'Inter', sans-serif !important;
        font-size: 12px;
        font-weight: 500;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: var(--text-tertiary) !important;
        border-bottom: 2px solid var(--text-primary);
    }

    .data-table td {
        padding: 12px 16px;
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 13px;
        border-bottom: 1px solid var(--border-subtle);
        color: var(--text-primary) !important;
    }

    .data-table tr:hover td {
        background: var(--bg-secondary);
    }

    .data-table td.positive { color: var(--positive) !important; }
    .data-table td.negative { color: var(--negative) !important; }

    /* Screener color legend */
    .screener-legend {
        font-family: 'Inter', sans-serif !important;
        font-size: 12px;
        color: var(--text-tertiary) !important;
        margin-bottom: 16px;
        padding: 12px 16px;
        background: var(--bg-secondary);
        border-left: 2px solid var(--border);
    }

    .screener-legend .neg { color: var(--negative); font-weight: 500; }
    .screener-legend .pos { color: var(--positive); font-weight: 500; }

    /* =========================================================
       Tabs
       ========================================================= */
    .stTabs [data-baseweb="tab-list"] {
        background: transparent;
        border-bottom: 1px solid var(--border);
        gap: 0;
    }

    .stTabs [data-baseweb="tab"] {
        background: transparent !important;
        border: none !important;
        color: var(--text-tertiary) !important;
        font-family: 'Bebas Neue', sans-serif !important;
        font-size: 18px !important;
        letter-spacing: 0.06em !important;
        text-transform: uppercase !important;
        padding: 16px 32px !important;
    }

    .stTabs [data-baseweb="tab"]:hover {
        color: var(--text-secondary) !important;
    }

    .stTabs [aria-selected="true"] {
        color: var(--text-primary) !important;
        border-bottom: 2px solid var(--text-primary) !important;
    }

    /* =========================================================
       Buttons & Inputs
       ========================================================= */
    .stButton > button {
        background: var(--text-primary) !important;
        border: 1px solid var(--text-primary) !important;
        color: white !important;
        font-family: 'Inter', sans-serif !important;
        font-size: 14px !important;
        font-weight: 500 !important;
        letter-spacing: 0.06em !important;
        text-transform: uppercase !important;
        padding: 14px 40px !important;
        transition: opacity 0.2s ease !important;
    }

    .stButton > button:hover {
        opacity: 0.85 !important;
    }

    /* Ensure button label text stays white on dark background */
    .stButton > button p,
    .stButton > button span {
        color: white !important;
    }

    .stSelectbox > div > div {
        background: white !important;
        border: 1px solid var(--border) !important;
        color: var(--text-primary) !important;
        font-family: 'Inter', sans-serif !important;
    }

    /* =========================================================
       Expanders (Learn More sections)
       ========================================================= */
    .stExpander {
        border: 1px solid var(--border-subtle) !important;
        border-left: 2px solid var(--border) !important;
        background: white !important;
        margin-bottom: 8px;
    }

    .stExpander summary {
        font-family: 'Inter', sans-serif !important;
        font-size: 13px !important;
        font-weight: 400 !important;
        color: var(--text-secondary) !important;
    }

    /* =========================================================
       Section Divider
       ========================================================= */
    .divider {
        height: 1px;
        background: var(--border);
        margin: 32px 0;
    }

    /* =========================================================
       Footer
       ========================================================= */
    .footer {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 24px 0;
        border-top: 1px solid var(--border);
        margin-top: 48px;
    }

    .footer-text {
        font-family: 'Inter', sans-serif !important;
        font-size: 10px;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        color: var(--text-tertiary) !important;
    }

    /* No signal state */
    .empty-state {
        text-align: center;
        padding: 80px 0;
    }

    .empty-state-text {
        font-family: 'Bebas Neue', sans-serif !important;
        font-size: 24px;
        letter-spacing: 0.08em;
        color: var(--text-tertiary) !important;
    }

    .empty-state-sub {
        font-family: 'Inter', sans-serif !important;
        font-size: 13px;
        color: var(--text-tertiary) !important;
        margin-top: 8px;
    }

    /* Data freshness */
    .freshness {
        font-family: 'Inter', sans-serif !important;
        font-size: 11px;
        color: var(--text-tertiary) !important;
        margin-bottom: 16px;
    }

    /* =========================================================
       Onboarding
       ========================================================= */
    .onboarding-container {
        max-width: 560px;
        margin: 0 auto;
        padding: 64px 0;
    }

    .onboarding-step {
        font-family: 'Inter', sans-serif !important;
        font-size: 12px;
        font-weight: 500;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: var(--text-tertiary) !important;
        margin-bottom: 8px;
    }

    .onboarding-question {
        font-family: 'Bebas Neue', sans-serif !important;
        font-size: 36px;
        letter-spacing: 0.06em;
        color: var(--text-primary) !important;
        line-height: 1.1;
        margin-bottom: 8px;
    }

    .onboarding-desc {
        font-family: 'Inter', sans-serif !important;
        font-size: 14px;
        font-weight: 300;
        color: var(--text-secondary) !important;
        line-height: 1.6;
        margin-bottom: 32px;
    }

    /* Mode badge */
    .mode-badge {
        font-family: 'Inter', sans-serif !important;
        font-size: 10px;
        font-weight: 600;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        padding: 3px 10px;
        border: 1px solid;
        display: inline-block;
    }

    .mode-badge.paper {
        color: var(--signal-hedge);
        border-color: var(--signal-hedge);
    }

    .mode-badge.live {
        color: var(--negative);
        border-color: var(--negative);
    }

    .mode-badge.browsing {
        color: var(--text-tertiary);
        border-color: var(--border);
    }
</style>
""", unsafe_allow_html=True)


# Live clock JS
components.html("""
<script>
(function() {
    'use strict';
    var parent = window.parent.document;
    function updateClock() {
        var el = parent.getElementById('live-clock');
        if (!el) return;
        var now = new Date();
        el.textContent = String(now.getHours()).padStart(2,'0') + ':' +
                         String(now.getMinutes()).padStart(2,'0') + ':' +
                         String(now.getSeconds()).padStart(2,'0');
    }
    setInterval(updateClock, 1000);
    setTimeout(updateClock, 300);
})();
</script>
""", height=0)


# =============================================================================
# Helper Functions
# =============================================================================

def get_optimal_entry_time(signal):
    """Calculate optimal entry time based on signal type and market conditions."""
    from datetime import timedelta
    now = datetime.now()

    if signal.signal_type == SignalType.PUT_OPPORTUNITY:
        if signal.strength.value >= 4:
            window = "10:00 - 10:30 AM ET"
            rationale = "Enter on morning rally exhaustion. Overbought conditions tend to reverse after initial buying pressure fades."
            action = f"Place limit order for {signal.symbol} puts at strike ${signal.suggested_strike:.2f} when underlying reaches ${signal.current_price * 1.005:.2f} or higher."
        else:
            window = "2:30 - 3:00 PM ET"
            rationale = "Enter during afternoon distribution. Institutional profit-taking often creates optimal put entry."
            action = f"Place limit order for {signal.symbol} puts at strike ${signal.suggested_strike:.2f}. Target 30-45 DTE expiration."
    elif signal.signal_type == SignalType.CALL_OPPORTUNITY:
        if signal.strength.value >= 4:
            window = "9:45 - 10:15 AM ET"
            rationale = "Enter after opening panic subsides. Oversold bounces tend to begin within first 30 minutes."
            action = f"Place limit order for {signal.symbol} calls at strike ${signal.suggested_strike:.2f} when underlying tests ${signal.current_price * 0.995:.2f}."
        else:
            window = "3:00 - 3:30 PM ET"
            rationale = "Enter before power hour. Short covering and momentum buying often accelerate into close."
            action = f"Place limit order for {signal.symbol} calls at strike ${signal.suggested_strike:.2f}. Target 30-45 DTE expiration."
    elif signal.signal_type == SignalType.HEDGE_SIGNAL:
        window = "11:30 AM - 1:00 PM ET"
        rationale = "Midday lull provides tighter spreads. Lower volume tends to mean better fill prices for protective positions."
        action = f"Buy {signal.symbol} puts at strike ${signal.suggested_strike:.2f} for portfolio protection. Consider 60-90 DTE for time decay buffer."
    else:
        window = "9:35 - 9:45 AM ET"
        rationale = "Capture initial directional momentum before market digests overnight news."
        action = f"Enter {signal.symbol} straddle or strangle at current price level. Expect 3-5% move within 5 sessions."

    next_window = get_next_window_time(now, window)

    return {
        "window": window,
        "rationale": rationale,
        "action": action,
        "next": next_window
    }


def get_next_window_time(now, window):
    """Determine when the next entry window occurs."""
    from datetime import timedelta
    start_str = window.split(" - ")[0]
    is_pm = "PM" in window
    hour = int(start_str.split(":")[0])
    minute = int(start_str.split(":")[1].split(" ")[0])

    if is_pm and hour != 12:
        hour += 12

    window_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

    if now.weekday() >= 5:
        days_until_monday = 7 - now.weekday()
        next_date = now + timedelta(days=days_until_monday)
        return f"Next: Monday {next_date.strftime('%b %d')} at {start_str}"

    if now > window_time:
        if now.weekday() == 4:
            next_date = now + timedelta(days=3)
            return f"Next: Monday {next_date.strftime('%b %d')} at {start_str}"
        else:
            next_date = now + timedelta(days=1)
            return f"Next: Tomorrow at {start_str}"

    return f"Next: Today at {start_str}"


def format_strength(strength_value):
    """Format signal strength as text."""
    levels = {5: "EXTREME", 4: "STRONG", 3: "MODERATE", 2: "FAIR", 1: "WEAK"}
    return levels.get(strength_value, "")


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


# =============================================================================
# Onboarding Flow
# =============================================================================

def show_onboarding():
    """Show the first-time setup flow. Returns True if profile was just created."""
    st.markdown("""<div class="onboarding-container">
<div class="headline headline-lg" style="margin-bottom: 8px;">VOLATILITY SCANNER</div>
<div class="onboarding-desc" style="font-size: 16px; margin-bottom: 48px;">
Your personal options trading tool. Let's set up your profile so everything is tailored to you.
</div>
</div>""", unsafe_allow_html=True)

    st.markdown('<div class="onboarding-step">STEP 1 OF 4</div>', unsafe_allow_html=True)
    st.markdown('<div class="onboarding-question">WHAT ARE YOU WORKING WITH?</div>', unsafe_allow_html=True)
    st.markdown('<div class="onboarding-desc">This helps us show you trades you can actually afford.</div>', unsafe_allow_html=True)

    budget = st.select_slider(
        "Budget",
        options=[500, 1000, 2500, 5000, 10000, 25000],
        value=1000,
        format_func=lambda x: f"${x:,}",
        label_visibility="collapsed",
    )

    st.markdown("---")

    st.markdown('<div class="onboarding-step">STEP 2 OF 4</div>', unsafe_allow_html=True)
    st.markdown('<div class="onboarding-question">HOW MUCH RISK CAN YOU STOMACH?</div>', unsafe_allow_html=True)

    risk_options = {
        "Conservative": "I'd rather make small, safe plays. Max 15% of budget per trade.",
        "Moderate": "I can handle some swings for better returns. Max 30% per trade.",
        "Aggressive": "I'm here to learn fast. Show me everything. Max 50% per trade.",
    }
    risk = st.radio(
        "Risk tolerance",
        list(risk_options.keys()),
        index=1,
        format_func=lambda x: f"{x} — {risk_options[x]}",
        label_visibility="collapsed",
    )

    st.markdown("---")

    st.markdown('<div class="onboarding-step">STEP 3 OF 4</div>', unsafe_allow_html=True)
    st.markdown('<div class="onboarding-question">WHERE ARE YOU AT?</div>', unsafe_allow_html=True)

    exp_options = {
        "beginner": "New to investing — still learning the basics",
        "intermediate": "Know stocks, learning options and technical analysis",
        "experienced": "Experienced trader — just show me the signals",
    }
    experience = st.radio(
        "Experience",
        list(exp_options.keys()),
        index=0,
        format_func=lambda x: f"{exp_options[x]}",
        label_visibility="collapsed",
    )

    st.markdown("---")

    st.markdown('<div class="onboarding-step">STEP 4 OF 4</div>', unsafe_allow_html=True)
    st.markdown('<div class="onboarding-question">CONNECT A TRADING ACCOUNT</div>', unsafe_allow_html=True)
    st.markdown('<div class="onboarding-desc">Optional — connect Alpaca to execute trades directly from the app. You can skip this and add it later in settings.</div>', unsafe_allow_html=True)

    connect_alpaca = st.checkbox("I want to connect my Alpaca account")

    alpaca_key = ""
    alpaca_secret = ""
    trading_mode = "browsing"

    if connect_alpaca:
        alpaca_key = st.text_input("Alpaca API Key", type="password")
        alpaca_secret = st.text_input("Alpaca Secret Key", type="password")
        trading_mode = st.radio(
            "Trading mode",
            ["paper", "live"],
            format_func=lambda x: {
                "paper": "Paper Trading — Practice with simulated money, zero risk",
                "live": "Live Trading — Real money, real trades",
            }[x],
            label_visibility="collapsed",
        )
        if trading_mode == "live":
            st.markdown("""<div style="font-family: 'Inter', sans-serif; font-size: 13px; color: var(--negative); padding: 12px 16px; border-left: 2px solid var(--negative); margin: 8px 0;">
<strong>Live trading uses real money.</strong> You are responsible for all trades placed through this app.
This tool provides educational signals, not financial advice.
</div>""", unsafe_allow_html=True)

    st.markdown("---")

    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("START SCANNING", use_container_width=True):
            if connect_alpaca and not (alpaca_key and alpaca_secret):
                st.error("Please enter both Alpaca API keys, or uncheck the connection box.")
                return False

            profile = UserProfile(
                budget=budget,
                risk_tolerance=risk.lower(),
                experience=experience,
                alpaca_api_key=alpaca_key,
                alpaca_secret_key=alpaca_secret,
                trading_mode=trading_mode if connect_alpaca else "browsing",
            )
            profile.save()
            st.session_state["profile"] = profile
            st.rerun()
            return True

    with col2:
        if st.button("JUST BROWSING", use_container_width=True):
            profile = UserProfile(
                budget=budget,
                risk_tolerance=risk.lower(),
                experience=experience,
                trading_mode="browsing",
            )
            profile.save()
            st.session_state["profile"] = profile
            st.rerun()
            return True

    return False


def get_profile() -> UserProfile:
    """Load profile from session state or disk."""
    if "profile" in st.session_state:
        return st.session_state["profile"]
    profile = UserProfile.load()
    if profile:
        st.session_state["profile"] = profile
    return profile


# =============================================================================
# Main Dashboard
# =============================================================================

def main():
    profile = get_profile()
    now = datetime.now()
    market_open = 9 <= now.hour < 16 and now.weekday() < 5
    market_status = "MARKET OPEN" if market_open else "MARKET CLOSED"

    mode_class = profile.mode_label.lower() if profile else "browsing"
    mode_label = profile.mode_label if profile else "BROWSING"
    budget_display = f"${profile.budget:,}" if profile else "$1,000"

    # Page Header
    st.markdown(f"""
    <div class="page-header">
        <div class="page-header-row">
            <div>
                <div class="headline headline-lg">VOLATILITY SCANNER</div>
                <div class="label" style="margin-top: 8px;">NASDAQ-100 OPTIONS SIGNAL DETECTION</div>
            </div>
            <div style="text-align: right;">
                <div style="margin-bottom: 8px;"><span class="mode-badge {mode_class}">{mode_label}</span></div>
                <div class="time-display">{now.strftime("%Y.%m.%d")}</div>
                <div class="time-display"><span id="live-clock">{now.strftime("%H:%M:%S")}</span> ET</div>
                <div class="market-status" style="margin-top: 8px;">
                    <span class="status-dot {'active' if market_open else ''}"></span>{market_status}
                </div>
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
        if st.button("SCAN"):
            st.cache_data.clear()

    # Determine symbols
    if scan_size == "TOP 20 NASDAQ":
        symbols = NASDAQ_100[:20]
    elif scan_size == "TOP 50 NASDAQ":
        symbols = NASDAQ_100[:50]
    else:
        symbols = NASDAQ_100

    # Run scan
    scan_time = datetime.now()
    with st.spinner("Scanning..."):
        try:
            screened, signals = run_scan(symbols)
        except Exception as e:
            st.error(f"Scan error: {e}")
            return

    # Data freshness
    st.markdown(f'<div class="freshness">Last scanned: {scan_time.strftime("%I:%M %p")} ET</div>', unsafe_allow_html=True)

    # Tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["SIGNALS", "SCREENER", "TRACKER", "DOCUMENTATION", "PROFILE"])

    # ─── SIGNALS TAB ───
    with tab1:

        # Metrics
        strong_signals = len([s for s in signals if s.strength.value >= 4])

        st.markdown(f"""
        <div class="metric-grid">
            <div class="metric-card">
                <div class="metric-card-label">Symbols Scanned</div>
                <div class="metric-card-value">{len(symbols)}</div>
            </div>
            <div class="metric-card">
                <div class="metric-card-label">Passed Filters</div>
                <div class="metric-card-value">{len(screened)}</div>
            </div>
            <div class="metric-card">
                <div class="metric-card-label">Active Signals</div>
                <div class="metric-card-value">{len(signals)}</div>
            </div>
            <div class="metric-card">
                <div class="metric-card-label">Strong Signals</div>
                <div class="metric-card-value">{strong_signals}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # PRIMARY SIGNAL HERO PANEL
        if signals:
            primary = max(signals, key=lambda s: (s.strength.value, s.risk_reward_ratio or 0))
            primary_timing = get_optimal_entry_time(primary)

            signal_class = {
                SignalType.PUT_OPPORTUNITY: "put",
                SignalType.CALL_OPPORTUNITY: "call",
                SignalType.HEDGE_SIGNAL: "hedge",
                SignalType.VOLATILITY_PLAY: "volatility"
            }.get(primary.signal_type, "hedge")

            action_text = {
                SignalType.PUT_OPPORTUNITY: "Buy puts at strike",
                SignalType.CALL_OPPORTUNITY: "Buy calls at strike",
                SignalType.HEDGE_SIGNAL: "Hedge with puts at",
                SignalType.VOLATILITY_PLAY: "Enter volatility play at"
            }.get(primary.signal_type, "Consider position at")

            st.markdown(f"""
            <div class="hero-panel {signal_class}">
                <div class="hero-label">PRIMARY SIGNAL</div>
                <div class="hero-content">
                    <div class="hero-section">
                        <span class="signal-type-badge {signal_class}">{primary.signal_type.value}</span>
                        <div class="hero-symbol">{primary.symbol}</div>
                        <div class="hero-price">${primary.current_price:.2f}</div>
                    </div>
                    <div class="hero-section">
                        <div class="timing-label">OPTIMAL ENTRY</div>
                        <div class="timing-value">{primary_timing['window']}</div>
                        <div class="timing-next">{primary_timing['next']}</div>
                    </div>
                    <div class="hero-section">
                        <div class="action-label">ACTION</div>
                        <div class="action-text">{action_text}</div>
                        <div style="font-family: 'JetBrains Mono', monospace; font-size: 20px; font-weight: 500; margin-top: 8px;">${primary.suggested_strike:.2f}</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="hero-panel">
                <div class="hero-label">PRIMARY SIGNAL</div>
                <div class="empty-state">
                    <div class="empty-state-text">SCANNING FOR OPPORTUNITIES</div>
                    <div class="empty-state-sub">No actionable signals in current scan</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        # MARKET OVERVIEW STRIP
        avg_rsi = sum(s.rsi for s in screened) / len(screened) if screened else 0
        overbought_count = len([s for s in screened if s.rsi > 70])
        oversold_count = len([s for s in screened if s.rsi < 30])
        high_vol_count = len([s for s in screened if s.volatility_regime in ('HIGH', 'EXTREME', 'high', 'extreme')])
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

        # Market summary (educational)
        market_summary = generate_market_summary(screened, signals)
        st.markdown(f'<div class="market-summary">{market_summary}</div>', unsafe_allow_html=True)

        if not signals:
            st.markdown("""
            <div class="empty-state">
                <div class="empty-state-text">NO ACTIONABLE SIGNALS DETECTED</div>
                <div class="empty-state-sub">Expand scan universe or wait for market conditions to change</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            for signal in signals:
                signal_class = {
                    SignalType.PUT_OPPORTUNITY: "put",
                    SignalType.CALL_OPPORTUNITY: "call",
                    SignalType.HEDGE_SIGNAL: "hedge",
                    SignalType.VOLATILITY_PLAY: "volatility"
                }.get(signal.signal_type, "hedge")

                timing = get_optimal_entry_time(signal)
                summary = generate_signal_summary(signal)

                price_str = f"${signal.current_price:.2f}" if signal.current_price else "-"
                strike_str = f"${signal.suggested_strike:.2f}" if signal.suggested_strike else None
                stop_str = f"${signal.stop_loss:.2f}" if signal.stop_loss else None
                target_str = f"${signal.target_price:.2f}" if signal.target_price else None
                rr_str = f"{signal.risk_reward_ratio:.1f}:1" if signal.risk_reward_ratio else None

                # Build signal card HTML
                data_items = f'''
                    <div class="signal-data-item">
                        <div class="signal-data-label">Current Price</div>
                        <div class="signal-data-value">{price_str}</div>
                    </div>'''

                if strike_str:
                    data_items += f'''
                    <div class="signal-data-item">
                        <div class="signal-data-label">Strike Price</div>
                        <div class="signal-data-value accent">{strike_str}</div>
                    </div>'''
                if stop_str:
                    data_items += f'''
                    <div class="signal-data-item">
                        <div class="signal-data-label">Stop Loss</div>
                        <div class="signal-data-value negative">{stop_str}</div>
                    </div>'''
                if target_str:
                    data_items += f'''
                    <div class="signal-data-item">
                        <div class="signal-data-label">Target Price</div>
                        <div class="signal-data-value positive">{target_str}</div>
                    </div>'''
                if rr_str:
                    data_items += f'''
                    <div class="signal-data-item">
                        <div class="signal-data-label">Risk/Reward</div>
                        <div class="signal-data-value">{rr_str}</div>
                    </div>'''

                # IV Rank inline
                iv_rank = signal.key_metrics.get("iv_rank")
                iv_html = ""
                if iv_rank is not None:
                    iv_explanation = generate_iv_explanation(iv_rank)
                    iv_html = f'<div class="iv-inline">{iv_explanation}</div>'

                risk = generate_risk_note(signal)

                st.markdown(f'''<div class="signal-card {signal_class}">
<div class="signal-header">
<div style="display: flex; align-items: center; gap: 16px;">
<span class="signal-type-badge {signal_class}">{signal.signal_type.value}</span>
<span class="signal-symbol">{signal.symbol}</span>
</div>
<div class="signal-strength-text">{format_strength(signal.strength.value)}</div>
</div>
<div class="signal-body">
<div class="signal-summary">{summary}</div>
<div class="signal-data-grid">{data_items}</div>
{iv_html}
<div class="timing-section">
<div class="timing-label">OPTIMAL ENTRY WINDOW</div>
<div class="timing-value">{timing['window']}</div>
<div class="timing-next">{timing['next']}</div>
<div class="timing-note">{timing['rationale']}</div>
</div>
<div class="action-section">
<div class="action-label">RECOMMENDED ACTION</div>
<div class="action-text">{timing['action']}</div>
</div>
<div class="risk-note"><strong>Risk:</strong> {risk}</div>
</div>
</div>''', unsafe_allow_html=True)

                # Educational expanders (Streamlit native — can't be in raw HTML)
                col_exp1, col_exp2, col_exp3 = st.columns(3)

                with col_exp1:
                    with st.expander("Why this strike price?"):
                        st.markdown(f'<div class="body-light">{generate_strike_explanation(signal)}</div>', unsafe_allow_html=True)

                with col_exp2:
                    with st.expander("Options breakdown"):
                        greeks = getattr(signal, "greeks", None)
                        if greeks:
                            greek_items = format_greeks_educational(greeks)
                            for g in greek_items:
                                st.markdown(f"""<div style="margin-bottom: 12px;">
<span style="font-family: 'JetBrains Mono', monospace; font-size: 13px; font-weight: 500;">{g['name']}: {g['value']}</span>
<div class="body-light" style="margin-top: 2px;">{g['explanation']}</div>
</div>""", unsafe_allow_html=True)
                        else:
                            st.markdown('<div class="body-light">Greeks data not available for this signal.</div>', unsafe_allow_html=True)

                with col_exp3:
                    with st.expander("Signal strength"):
                        breakdown = generate_strength_breakdown(signal)
                        st.code(breakdown, language=None)

    # ─── SCREENER TAB ───
    with tab2:
        if not screened:
            st.markdown("""
            <div class="empty-state">
                <div class="empty-state-text">NO DATA</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="screener-legend">
                <span class="neg">Red RSI</span> = overbought (may pull back) &nbsp;&middot;&nbsp;
                <span class="pos">Green RSI</span> = oversold (may bounce) &nbsp;&middot;&nbsp;
                Regime = how volatile the stock is acting compared to normal
            </div>
            """, unsafe_allow_html=True)

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
                    <td style="text-transform: uppercase; font-size: 11px; letter-spacing: 1px;">{regime_str}</td>
                </tr>'''

            st.markdown(f"""
            <table class="data-table">
                <thead>
                    <tr>
                        <th>Symbol</th>
                        <th>Price</th>
                        <th>Change</th>
                        <th title="Momentum score (0-100). Above 70 = overbought, below 30 = oversold">RSI</th>
                        <th title="How volatile vs last 100 days. Higher = more movement">ATR Percentile</th>
                        <th title="How much the price swings per year, as a percent">Historical Vol</th>
                        <th title="Volatility level: LOW / NORMAL / HIGH / EXTREME">Regime</th>
                    </tr>
                </thead>
                <tbody>
                    {table_rows}
                </tbody>
            </table>
            """, unsafe_allow_html=True)

    # ─── TRACKER TAB ───
    with tab3:
        tracker = PredictionTracker()

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

        price_data = {s.symbol: s.current_price for s in screened}
        tracker.check_and_update_predictions(price_data)
        tracker.expire_old_predictions()

        stats = tracker.get_statistics()

        win_color = "var(--positive)" if stats['win_rate'] >= 50 else "var(--negative)"

        st.markdown(f"""
        <div class="headline headline-sm" style="margin-bottom: 24px;">PREDICTION PERFORMANCE</div>

        <div class="metric-grid">
            <div class="metric-card">
                <div class="metric-card-label">Total Predictions</div>
                <div class="metric-card-value">{stats['total_predictions']}</div>
            </div>
            <div class="metric-card">
                <div class="metric-card-label">Win Rate</div>
                <div class="metric-card-value" style="color: {win_color} !important;">{stats['win_rate']:.1f}%</div>
            </div>
            <div class="metric-card">
                <div class="metric-card-label">Wins / Losses</div>
                <div class="metric-card-value"><span style="color: var(--positive);">{stats['wins']}</span> / <span style="color: var(--negative);">{stats['losses']}</span></div>
            </div>
            <div class="metric-card">
                <div class="metric-card-label">Pending</div>
                <div class="metric-card-value">{stats['pending']}</div>
            </div>
        </div>

        <div class="metric-grid">
            <div class="metric-card">
                <div class="metric-card-label">Avg Win</div>
                <div class="metric-card-value" style="color: var(--positive) !important;">+{stats['avg_win_pct']:.1f}%</div>
            </div>
            <div class="metric-card">
                <div class="metric-card-label">Avg Loss</div>
                <div class="metric-card-value" style="color: var(--negative) !important;">{stats['avg_loss_pct']:.1f}%</div>
            </div>
            <div class="metric-card">
                <div class="metric-card-label">Profit Factor</div>
                <div class="metric-card-value">{stats['profit_factor']:.2f}</div>
            </div>
            <div class="metric-card">
                <div class="metric-card-label">Last 30 Days</div>
                <div class="metric-card-value">{stats['recent_30d']['win_rate']:.0f}%</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        if stats['by_signal_type']:
            st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
            st.markdown('<div class="headline headline-sm" style="margin-bottom: 16px;">BY SIGNAL TYPE</div>', unsafe_allow_html=True)

            type_rows = ""
            for sig_type, data in stats['by_signal_type'].items():
                type_rows += f"""
                <tr>
                    <td style="font-weight: 600;">{sig_type}</td>
                    <td>{data['total']}</td>
                    <td class="positive">{data['wins']}</td>
                    <td class="negative">{data['losses']}</td>
                    <td style="color: {'var(--positive)' if data['win_rate'] >= 50 else 'var(--negative)'};">{data['win_rate']:.1f}%</td>
                </tr>
                """

            st.markdown(f"""
            <table class="data-table">
                <thead><tr><th>Signal Type</th><th>Total</th><th>Wins</th><th>Losses</th><th>Win Rate</th></tr></thead>
                <tbody>{type_rows}</tbody>
            </table>
            """, unsafe_allow_html=True)

        st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
        st.markdown('<div class="headline headline-sm" style="margin-bottom: 16px;">RECENT PREDICTIONS</div>', unsafe_allow_html=True)

        predictions = tracker.get_predictions(limit=20)

        if predictions:
            pred_rows = ""
            for pred in predictions:
                status_color = {
                    PredictionStatus.WIN: "var(--positive)",
                    PredictionStatus.LOSS: "var(--negative)",
                    PredictionStatus.PENDING: "var(--signal-hedge)",
                    PredictionStatus.EXPIRED: "var(--text-tertiary)",
                    PredictionStatus.CANCELLED: "var(--text-tertiary)"
                }.get(pred.status, "inherit")

                profit_display = f"{pred.profit_pct:+.1f}%" if pred.profit_pct is not None else "-"
                profit_class = "positive" if pred.profit_pct and pred.profit_pct > 0 else "negative" if pred.profit_pct and pred.profit_pct < 0 else ""

                outcome_display = f"${pred.outcome_price:.2f}" if pred.outcome_price else "-"
                date_display = pred.created_at.strftime('%m/%d %H:%M') if pred.created_at else '-'

                pred_rows += f"""
                <tr>
                    <td>{date_display}</td>
                    <td style="font-weight: 600;">{pred.symbol}</td>
                    <td>{pred.signal_type}</td>
                    <td>${pred.entry_price:.2f}</td>
                    <td>{outcome_display}</td>
                    <td class="{profit_class}">{profit_display}</td>
                    <td style="color: {status_color}; text-transform: uppercase;">{pred.status.value}</td>
                </tr>
                """

            st.markdown(f"""
            <table class="data-table">
                <thead><tr><th>Date</th><th>Symbol</th><th>Type</th><th>Entry</th><th>Outcome</th><th>P/L</th><th>Status</th></tr></thead>
                <tbody>{pred_rows}</tbody>
            </table>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="empty-state">
                <div class="empty-state-text">NO PREDICTIONS YET</div>
                <div class="empty-state-sub">Predictions appear as signals are generated</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
        st.markdown('<div class="headline headline-sm" style="margin-bottom: 16px;">MANUAL RESOLUTION</div>', unsafe_allow_html=True)

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
            st.markdown('<div class="body-light">No pending predictions to resolve.</div>', unsafe_allow_html=True)

    # ─── DOCUMENTATION TAB ───
    with tab4:
        st.markdown('<div class="headline headline-sm" style="margin-bottom: 20px;">SIGNAL TYPES</div>', unsafe_allow_html=True)
        st.markdown("""
        <table class="data-table">
        <thead><tr><th>Type</th><th>What It Means</th><th>Action</th></tr></thead>
        <tbody>
        <tr><td style="color: var(--signal-bearish); font-weight: 600;">PUT</td>
            <td>The stock has been rising too fast (RSI above 70, price above its normal range). Historically, these stretched conditions tend to snap back.</td>
            <td>Buy put options to profit from a potential decline</td></tr>
        <tr><td style="color: var(--signal-bullish); font-weight: 600;">CALL</td>
            <td>The stock has been beaten down (RSI below 30, price below its normal range). Oversold stocks often bounce back.</td>
            <td>Buy call options to profit from a potential recovery</td></tr>
        <tr><td style="color: var(--signal-hedge); font-weight: 600;">HEDGE</td>
            <td>Volatility is very high — the market is chaotic. This isn't a directional bet; it's protection.</td>
            <td>Buy protective puts on positions you already own</td></tr>
        <tr><td style="color: var(--signal-volatility); font-weight: 600;">VOLATILITY</td>
            <td>The stock is swinging wildly but options are cheap. The market hasn't priced in the actual movement yet.</td>
            <td>Buy a straddle (call + put) to profit from a big move in either direction</td></tr>
        </tbody>
        </table>
        """, unsafe_allow_html=True)

        st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

        st.markdown('<div class="headline headline-sm" style="margin-bottom: 20px;">ENTRY TIMING</div>', unsafe_allow_html=True)
        st.markdown("""
        <table class="data-table">
        <thead><tr><th>Signal</th><th>Window</th><th>Why This Time</th></tr></thead>
        <tbody>
        <tr><td>PUT (Strong)</td><td>10:00-10:30 AM</td><td>Morning buying often exhausts here — sellers step in after the initial rush</td></tr>
        <tr><td>PUT (Moderate)</td><td>2:30-3:00 PM</td><td>Institutional profit-taking in the afternoon creates natural selling pressure</td></tr>
        <tr><td>CALL (Strong)</td><td>9:45-10:15 AM</td><td>Opening panic tends to exhaust quickly — rebounds start within 30 minutes</td></tr>
        <tr><td>CALL (Moderate)</td><td>3:00-3:30 PM</td><td>Short covering and momentum buying often accelerate before market close</td></tr>
        <tr><td>HEDGE</td><td>11:30 AM-1:00 PM</td><td>Midday is quieter — tighter bid/ask spreads mean better prices for protection</td></tr>
        </tbody>
        </table>
        """, unsafe_allow_html=True)

        st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

        st.markdown('<div class="headline headline-sm" style="margin-bottom: 20px;">INDICATOR DEFINITIONS</div>', unsafe_allow_html=True)
        st.markdown("""
        <table class="data-table">
        <thead><tr><th>Indicator</th><th>What It Measures</th><th>Key Levels</th></tr></thead>
        <tbody>
        <tr><td>RSI</td><td>Momentum — how aggressively the stock has been bought or sold over the last 14 days</td><td>Above 70 = overbought (may drop). Below 30 = oversold (may bounce)</td></tr>
        <tr><td>ATR Percentile</td><td>How volatile the stock is compared to its own last 100 days of movement</td><td>Above 70% = elevated volatility. Above 90% = extreme</td></tr>
        <tr><td>Historical Vol</td><td>How much the price typically swings per year, based on the last 20 days</td><td>Above 40% is considered high volatility</td></tr>
        <tr><td>BB %B</td><td>Where the price sits within its normal range (Bollinger Bands)</td><td>Above 1.0 = above the range (bearish signal). Below 0.0 = below the range (bullish signal)</td></tr>
        <tr><td>IV Rank</td><td>How expensive options are now compared to the last year</td><td>Above 50 = pricier than average. Below 30 = cheap (good time to buy options)</td></tr>
        </tbody>
        </table>
        """, unsafe_allow_html=True)

        st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

        st.markdown("""
        <div class="body-light" style="margin-top: 24px; font-size: 11px; color: var(--text-tertiary);">
        This scanner provides analytical signals for informational and educational purposes only. It does not constitute financial advice.
        Options trading involves substantial risk of loss. Past performance does not guarantee future results.
        Conduct independent research and consider consulting a licensed financial advisor before making investment decisions.
        </div>
        """, unsafe_allow_html=True)

    # ─── PROFILE TAB ───
    with tab5:
        st.markdown('<div class="headline headline-sm" style="margin-bottom: 4px;">YOUR PROFILE</div>', unsafe_allow_html=True)
        st.markdown('<div class="onboarding-desc" style="margin-bottom: 24px;">Adjust anytime — changes apply to the next scan.</div>', unsafe_allow_html=True)

        prof_col1, prof_col2 = st.columns(2)

        with prof_col1:
            st.markdown('<div class="label" style="margin-bottom: 4px;">BUDGET</div>', unsafe_allow_html=True)
            new_budget = st.select_slider(
                "Budget",
                options=[500, 1000, 2500, 5000, 10000, 25000],
                value=profile.budget,
                format_func=lambda x: f"${x:,}",
                label_visibility="collapsed",
                key="prof_budget",
            )

            st.markdown('<div class="label" style="margin-top: 24px; margin-bottom: 4px;">RISK TOLERANCE</div>', unsafe_allow_html=True)
            risk_map = {"conservative": 0, "moderate": 1, "aggressive": 2}
            risk_labels = ["Conservative", "Moderate", "Aggressive"]
            risk_desc = {
                "Conservative": "Small, safe plays. Max 15% of budget per trade.",
                "Moderate": "Some swings for better returns. Max 30% per trade.",
                "Aggressive": "Show me everything. Max 50% per trade.",
            }
            new_risk = st.radio(
                "Risk",
                risk_labels,
                index=risk_map.get(profile.risk_tolerance, 1),
                label_visibility="collapsed",
                key="prof_risk",
            )
            st.markdown(f'<div class="body-light" style="font-size: 12px; margin-top: -8px;">{risk_desc[new_risk]}</div>', unsafe_allow_html=True)

        with prof_col2:
            st.markdown('<div class="label" style="margin-bottom: 4px;">EXPERIENCE LEVEL</div>', unsafe_allow_html=True)
            exp_map = {"beginner": 0, "intermediate": 1, "experienced": 2}
            exp_labels = ["Beginner", "Intermediate", "Experienced"]
            new_exp = st.radio(
                "Experience",
                exp_labels,
                index=exp_map.get(profile.experience, 0),
                label_visibility="collapsed",
                key="prof_exp",
            )

            st.markdown('<div class="label" style="margin-top: 24px; margin-bottom: 8px;">TRADING ACCOUNT</div>', unsafe_allow_html=True)
            if profile.is_connected:
                mode_class = profile.trading_mode
                st.markdown(f'<div style="margin-bottom: 12px;"><span class="mode-badge {mode_class}">{profile.mode_label}</span> <span style="font-family: Inter, sans-serif; font-size: 12px; color: var(--text-tertiary);">Alpaca connected</span></div>', unsafe_allow_html=True)
                new_mode = st.radio(
                    "Mode",
                    ["paper", "live"],
                    index=0 if profile.trading_mode == "paper" else 1,
                    format_func=lambda x: "Paper Trading" if x == "paper" else "Live Trading",
                    label_visibility="collapsed",
                    key="prof_mode",
                )
            else:
                st.markdown('<div style="font-family: Inter, sans-serif; font-size: 13px; color: var(--text-tertiary); margin-bottom: 12px;">No account connected.</div>', unsafe_allow_html=True)
                new_mode = "browsing"
                connect = st.checkbox("Connect Alpaca account", key="prof_connect")
                if connect:
                    new_key = st.text_input("API Key", type="password", key="prof_key")
                    new_secret = st.text_input("Secret Key", type="password", key="prof_secret")
                    new_mode = st.radio(
                        "Mode",
                        ["paper", "live"],
                        format_func=lambda x: "Paper Trading" if x == "paper" else "Live Trading",
                        label_visibility="collapsed",
                        key="prof_new_mode",
                    )
                    if new_key and new_secret:
                        profile.alpaca_api_key = new_key
                        profile.alpaca_secret_key = new_secret

        st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

        # Profile summary card
        max_pos = profile.max_position_dollars
        st.markdown(f"""<div style="background: white; border: 1px solid var(--border-subtle); padding: 24px; max-width: 480px;">
<div class="label" style="margin-bottom: 16px;">PROFILE SUMMARY</div>
<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px;">
<div>
<div class="signal-data-label">BUDGET</div>
<div class="signal-data-value">${profile.budget:,}</div>
</div>
<div>
<div class="signal-data-label">MAX POSITION</div>
<div class="signal-data-value">${max_pos:,.0f}</div>
</div>
<div>
<div class="signal-data-label">RISK LEVEL</div>
<div class="signal-data-value" style="font-size: 16px;">{profile.risk_tolerance.title()}</div>
</div>
<div>
<div class="signal-data-label">MODE</div>
<div class="signal-data-value" style="font-size: 16px;">{profile.mode_label}</div>
</div>
</div>
</div>""", unsafe_allow_html=True)

        # Save changes automatically
        changed = (
            new_budget != profile.budget
            or new_risk.lower() != profile.risk_tolerance
            or new_exp.lower() != profile.experience
            or new_mode != profile.trading_mode
        )
        if changed:
            profile.budget = new_budget
            profile.risk_tolerance = new_risk.lower()
            profile.experience = new_exp.lower()
            profile.trading_mode = new_mode
            profile.save()
            st.session_state["profile"] = profile

        st.markdown("---")
        if st.button("RESET PROFILE & START OVER"):
            UserProfile.delete()
            if "profile" in st.session_state:
                del st.session_state["profile"]
            st.rerun()

    # Footer
    st.markdown(f"""
    <div class="footer">
        <span class="footer-text">VOLATILITY SCANNER v4.0</span>
        <span class="footer-text">DATA SOURCE: YAHOO FINANCE / ALPACA MARKETS</span>
    </div>
    """, unsafe_allow_html=True)


def app():
    """Entry point — shows onboarding or main dashboard."""
    profile = get_profile()

    if profile is None:
        show_onboarding()
    else:
        main()


if __name__ == "__main__":
    app()
