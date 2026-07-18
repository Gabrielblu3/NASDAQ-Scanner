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
_FAVICON_PATH = str(Path(__file__).parent / "assets" / "favicon.jpeg")

st.set_page_config(
    page_title="VOLATILITY TERMINAL",
    page_icon=_FAVICON_PATH,
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

        /* 2026 — accent, gradients, glows, motion */
        --accent: #00D87A;
        --accent-soft: #00B86A;
        --accent-glow: 0 0 24px rgba(0,216,122,0.45), 0 0 60px rgba(0,216,122,0.18);
        --grad-bg: radial-gradient(1200px 600px at 15% -10%, #F4FBF7 0%, rgba(250,250,250,0) 55%),
                   radial-gradient(900px 500px at 110% 10%, #F6F4FB 0%, rgba(250,250,250,0) 60%);
        --grad-panel: linear-gradient(180deg, #FFFFFF 0%, #FAFAFA 100%);
        --shadow-soft: 0 1px 2px rgba(20,20,30,0.04), 0 8px 24px rgba(20,20,30,0.06);
        --shadow-lift: 0 2px 4px rgba(20,20,30,0.06), 0 16px 48px rgba(20,20,30,0.10);
        --ease-out: cubic-bezier(0.22, 1, 0.36, 1);
    }

    /* =========================================================
       Keyframes
       ========================================================= */
    @keyframes boot-fade {
        0% { opacity: 1; }
        70% { opacity: 1; }
        100% { opacity: 0; visibility: hidden; }
    }
    @keyframes boot-pulse {
        0%, 100% { transform: scale(1); opacity: 0.6; }
        50% { transform: scale(1.4); opacity: 1; }
    }
    @keyframes rise-in {
        from { opacity: 0; transform: translateY(12px); }
        to { opacity: 1; transform: translateY(0); }
    }
    @keyframes sweep {
        from { background-position: -200% 0; }
        to { background-position: 200% 0; }
    }
    @keyframes breathe {
        0%, 100% {
            box-shadow: 0 0 24px rgba(0,216,122,0.45), 0 0 60px rgba(0,216,122,0.18),
                        0 1px 2px rgba(20,20,30,0.04), 0 8px 24px rgba(20,20,30,0.06);
        }
        50% {
            box-shadow: 0 0 32px rgba(0,216,122,0.60), 0 0 80px rgba(0,216,122,0.25),
                        0 1px 2px rgba(20,20,30,0.04), 0 8px 24px rgba(20,20,30,0.06);
        }
    }
    @keyframes live-pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.55; }
    }
    @keyframes scan-pulse {
        0%   { background-position: 0% 50%; }
        50%  { background-position: -160% 50%; }
        100% { background-position: -320% 50%; }
    }
    /* Gradient flow whenever Streamlit's spinner is anywhere in the app (i.e. a scan is running). */
    .stApp:has([data-testid="stSpinner"]) .stButton > button[kind="primary"],
    .stApp:has(.stSpinner) .stButton > button[kind="primary"] {
        animation: scan-pulse 4.5s ease-in-out infinite !important;
    }
    /* Smooth click feedback — pure CSS, no JS. Pressing dips the button + intensifies glow,
       releasing transitions back over 0.35s. */
    .stButton > button[kind="primary"] {
        transition: transform 0.35s var(--ease-out), box-shadow 0.35s var(--ease-out), background-position 0.6s var(--ease-out) !important;
    }
    .stButton > button[kind="primary"]:active {
        transform: scale(0.97) !important;
        box-shadow: 0 0 36px rgba(0,216,122,0.70), 0 0 90px rgba(0,216,122,0.30), var(--shadow-lift) !important;
    }
    @keyframes post-onboard-in {
        from { opacity: 0; transform: translateY(8px); }
        to   { opacity: 1; transform: translateY(0); }
    }
    .stApp.post-onboard .main .block-container {
        animation: post-onboard-in 0.7s var(--ease-out) both;
    }
    /* During the onboard→main transition, hide any stray onboarding container left over from the previous run. */
    .stApp.post-onboard .onboarding-container {
        display: none !important;
    }

    /* =========================================================
       Boot Veil
       ========================================================= */
    #boot-veil {
        position: fixed;
        inset: 0;
        z-index: 99999;
        background: #FAFAFA;
        background-image: var(--grad-bg);
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        gap: 28px;
        animation: boot-fade 1.7s var(--ease-out) forwards;
        pointer-events: none;
    }
    #boot-veil .wordmark {
        font-family: 'Bebas Neue', 'Arial Narrow', sans-serif;
        font-size: 56px;
        letter-spacing: 0.18em;
        background: linear-gradient(90deg, #1A1A1A 0%, #1A1A1A 35%, #00D87A 50%, #1A1A1A 65%, #1A1A1A 100%);
        background-size: 200% 100%;
        -webkit-background-clip: text;
        background-clip: text;
        -webkit-text-fill-color: transparent;
        animation: sweep 2s linear infinite;
    }
    #boot-veil .dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: var(--accent);
        box-shadow: 0 0 16px var(--accent), 0 0 32px rgba(0,216,122,0.5);
        animation: boot-pulse 1.2s var(--ease-out) infinite;
    }
    @media (prefers-reduced-motion: reduce) {
        #boot-veil { animation: boot-fade 0.4s linear forwards; }
        #boot-veil .dot, #boot-veil .wordmark { animation: none; }
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
        background-image: var(--grad-bg) !important;
        background-attachment: fixed !important;
    }

    .main .block-container {
        background-color: transparent;
        padding: 32px 48px;
        max-width: 1200px;
    }

    @media (prefers-reduced-motion: no-preference) {
        .page-header { animation: rise-in 0.7s var(--ease-out) both; animation-delay: 0.10s; }
        .stTabs      { animation: rise-in 0.7s var(--ease-out) both; animation-delay: 0.30s; }
        .metric-grid, .hero-panel, .market-strip, .signal-card {
            animation: rise-in 0.7s var(--ease-out) both;
            animation-delay: 0.20s;
        }
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

    /* Bebas Neue must win over the .stMarkdown div blanket above */
    .stMarkdown .headline,
    .stMarkdown .headline-lg,
    .stMarkdown .headline-md,
    .stMarkdown .headline-sm,
    .stMarkdown .onboarding-question,
    .stMarkdown .hero-symbol,
    .stMarkdown .signal-symbol,
    .stMarkdown .signal-type-badge,
    .stMarkdown .empty-state-text {
        font-family: 'Bebas Neue', 'Arial Narrow', sans-serif !important;
    }
    .stMarkdown .mono,
    .stMarkdown .metric-card-value,
    .stMarkdown .hero-price,
    .stMarkdown .signal-data-value,
    .stMarkdown .market-strip-value,
    .stMarkdown .timing-value,
    .stMarkdown .time-display {
        font-family: 'JetBrains Mono', 'Consolas', monospace !important;
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
        background: var(--accent);
        box-shadow: 0 0 8px var(--accent), 0 0 16px rgba(0,216,122,0.4);
        animation: live-pulse 1.6s ease-in-out infinite;
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
        background: var(--grad-panel);
        border: 1px solid var(--border-subtle);
        padding: 20px 24px;
        border-radius: 4px;
        box-shadow: var(--shadow-soft);
        transition: transform 0.3s var(--ease-out), box-shadow 0.3s var(--ease-out);
    }
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: var(--shadow-lift);
    }

    /* =========================================================
       Polymarket — top trades of the day
       ========================================================= */
    .poly-hero {
        display: block;
        background: var(--grad-panel);
        border: 1px solid var(--border);
        border-left: 4px solid var(--accent);
        border-radius: 4px;
        padding: 24px 28px;
        margin-bottom: var(--space-lg);
        box-shadow: var(--shadow-soft);
        text-decoration: none !important;
        color: inherit !important;
        transition: transform 0.3s var(--ease-out), box-shadow 0.3s var(--ease-out);
    }
    .poly-hero:hover {
        transform: translateY(-2px);
        box-shadow: var(--shadow-lift);
    }
    .poly-hero-label {
        font-family: 'Inter', sans-serif !important;
        font-size: 12px;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        color: var(--text-tertiary) !important;
        margin-bottom: 16px;
    }
    .poly-hero-grid {
        display: grid;
        grid-template-columns: 2fr 1fr 1fr 1fr;
        gap: 24px;
        align-items: start;
    }
    .poly-hero-cat {
        font-family: 'Inter', sans-serif !important;
        font-size: 11px;
        font-weight: 600;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        color: var(--accent-soft) !important;
        margin-bottom: 6px;
    }
    .poly-hero-q {
        font-family: 'Inter', sans-serif !important;
        font-size: 20px;
        font-weight: 600;
        line-height: 1.3;
        color: var(--text-primary) !important;
    }
    .poly-hero-stat-label {
        font-family: 'Inter', sans-serif !important;
        font-size: 11px;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        color: var(--text-tertiary) !important;
        margin-bottom: 6px;
    }
    .poly-hero-stat-value {
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 26px;
        font-weight: 500;
        color: var(--text-primary) !important;
    }
    .poly-hero-sub {
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 11px;
        color: var(--text-tertiary) !important;
        margin-top: 6px;
    }
    .poly-hero-sub-num {
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 11px;
    }
    .poly-hero-read {
        margin-top: 18px;
        padding-top: 16px;
        border-top: 1px solid var(--border-subtle);
        font-family: 'Inter', sans-serif !important;
        font-size: 13px;
        line-height: 1.55;
        color: var(--text-secondary) !important;
    }

    .poly-badge {
        display: inline-block;
        font-family: 'Inter', sans-serif !important;
        font-size: 9px;
        font-weight: 600;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        padding: 4px 8px;
        border-radius: 3px;
        border: 1px solid var(--border);
        white-space: nowrap;
        margin-right: 10px;
        vertical-align: middle;
    }
    .poly-badge.pos {
        color: var(--positive) !important;
        border-color: var(--positive);
        background: var(--signal-bullish-bg);
    }
    .poly-badge.neg {
        color: var(--negative) !important;
        border-color: var(--negative);
        background: var(--signal-bearish-bg);
    }
    .poly-badge.warn {
        color: var(--signal-hedge) !important;
        border-color: var(--signal-hedge);
        background: var(--signal-hedge-bg);
    }
    .poly-badge.neutral {
        color: var(--text-tertiary) !important;
        border-color: var(--border);
        background: var(--bg-secondary);
    }

    .poly-row-head, .poly-row {
        display: grid;
        grid-template-columns: 32px minmax(0, 1fr) 56px 56px 84px 64px 76px 104px;
        gap: 14px;
        align-items: center;
    }
    .poly-row-head {
        padding: 0 18px 8px 18px;
        font-family: 'Inter', sans-serif !important;
        font-size: 10px;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: var(--text-tertiary) !important;
    }
    .poly-rows {
        display: flex;
        flex-direction: column;
        gap: 10px;
        margin-bottom: var(--space-xl);
    }
    .poly-row {
        position: relative;
        background: var(--grad-panel);
        border: 1px solid var(--border-subtle);
        border-left: 3px solid var(--accent);
        border-radius: 4px;
        padding: 14px 18px;
        box-shadow: var(--shadow-soft);
        text-decoration: none !important;
        color: inherit !important;
        transition: transform 0.25s var(--ease-out), box-shadow 0.25s var(--ease-out), border-color 0.25s var(--ease-out);
    }
    .poly-row:hover {
        transform: translateY(-2px);
        box-shadow: var(--shadow-lift);
        border-color: var(--accent);
        z-index: 20;
    }
    .poly-rank {
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 13px;
        color: var(--text-tertiary) !important;
    }
    .poly-q {
        font-family: 'Inter', sans-serif !important;
        font-size: 13px;
        font-weight: 500;
        color: var(--text-primary) !important;
        line-height: 1.35;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
    }
    .poly-cat {
        display: block;
        font-family: 'Inter', sans-serif !important;
        font-size: 10px;
        letter-spacing: 0.05em;
        text-transform: uppercase;
        color: var(--text-tertiary) !important;
        margin-top: 3px;
    }
    .poly-num {
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 14px;
        color: var(--text-primary) !important;
    }
    .poly-yes {
        color: var(--accent-soft) !important;
        font-weight: 600;
    }
    .poly-no {
        color: var(--text-secondary) !important;
    }
    .poly-pos { color: var(--positive) !important; }
    .poly-neg { color: var(--negative) !important; }
    .poly-meta {
        font-family: 'Inter', sans-serif !important;
        font-size: 12px;
        letter-spacing: 0.04em;
        text-transform: uppercase;
        color: var(--text-secondary) !important;
    }

    /* Hover tooltip — extra depth on each trade */
    .poly-tooltip {
        position: absolute;
        top: calc(100% + 6px);
        left: 30px;
        right: 30px;
        background: #FFFFFF;
        border: 1px solid var(--accent);
        border-radius: 4px;
        padding: 16px 20px;
        box-shadow: var(--shadow-lift);
        opacity: 0;
        visibility: hidden;
        transform: translateY(-4px);
        transition: opacity 0.2s var(--ease-out), transform 0.2s var(--ease-out), visibility 0.2s;
        z-index: 60;
        pointer-events: none;
    }
    .poly-row:hover .poly-tooltip {
        opacity: 1;
        visibility: visible;
        transform: translateY(0);
    }
    .poly-tooltip-read {
        font-family: 'Inter', sans-serif !important;
        font-size: 12px;
        line-height: 1.55;
        color: var(--text-primary) !important;
        padding: 10px 14px;
        border-left: 2px solid var(--accent);
        background: rgba(0, 216, 122, 0.06);
        border-radius: 0 3px 3px 0;
        margin-bottom: 14px;
        white-space: normal;
    }
    .poly-tooltip-desc {
        font-family: 'Inter', sans-serif !important;
        font-size: 12px;
        color: var(--text-secondary) !important;
        line-height: 1.55;
        margin-top: 14px;
        display: -webkit-box;
        -webkit-line-clamp: 3;
        -webkit-box-orient: vertical;
        overflow: hidden;
        white-space: normal;
    }
    .poly-tooltip-grid {
        display: grid;
        grid-template-columns: repeat(6, 1fr);
        gap: 12px;
    }
    .poly-tooltip-label {
        font-family: 'Inter', sans-serif !important;
        font-size: 10px;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        color: var(--text-tertiary) !important;
        margin-bottom: 4px;
    }
    .poly-tooltip-value {
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 13px;
        color: var(--text-primary) !important;
    }
    .poly-tooltip-hint {
        font-family: 'Inter', sans-serif !important;
        font-size: 10px;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: var(--accent-soft) !important;
        margin-top: 12px;
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
        background: var(--grad-panel);
        border: 1px solid var(--border);
        border-left: 4px solid var(--text-primary);
        margin-bottom: var(--space-xl);
        border-radius: 4px;
        box-shadow: var(--shadow-soft);
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
        background: var(--grad-panel);
        border: 1px solid var(--border);
        border-left: 3px solid var(--text-primary);
        margin-bottom: var(--space-lg);
        border-radius: 4px;
        box-shadow: var(--shadow-soft);
        transition: transform 0.3s var(--ease-out), box-shadow 0.3s var(--ease-out);
    }
    .signal-card:hover {
        transform: translateY(-2px);
        box-shadow: var(--shadow-lift);
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
        background: var(--grad-panel);
        border: 1px solid var(--border);
        margin-bottom: var(--space-lg);
        border-radius: 4px;
        box-shadow: var(--shadow-soft);
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

    .stTabs [data-baseweb="tab"] {
        position: relative !important;
        transition: color 0.25s var(--ease-out) !important;
    }
    .stTabs [data-baseweb="tab"]::after {
        content: "";
        position: absolute;
        left: 32px;
        right: 32px;
        bottom: 0;
        height: 2px;
        background: linear-gradient(90deg, rgba(0,216,122,0.35) 0%, var(--accent) 50%, rgba(0,216,122,0.35) 100%);
        transform: scaleX(0);
        transform-origin: left center;
        transition: transform 0.35s var(--ease-out);
    }
    .stTabs [aria-selected="true"] {
        color: var(--text-primary) !important;
        border-bottom: none !important;
        box-shadow: none !important;
    }
    .stTabs [aria-selected="true"]::after {
        transform: scaleX(1);
    }
    /* Kill baseweb's built-in dark active-tab indicator */
    .stTabs [data-baseweb="tab-highlight"],
    .stTabs [data-baseweb="tab-border"] {
        background: transparent !important;
        background-color: transparent !important;
        height: 0 !important;
        display: none !important;
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
        border-radius: 2px !important;
        transition: opacity 0.2s ease, transform 0.25s var(--ease-out), box-shadow 0.25s var(--ease-out) !important;
    }

    .stButton > button:hover {
        opacity: 0.85 !important;
    }

    /* Primary CTA — the SCAN button. Static at rest, animates only on click / during scan. */
    .stButton > button[kind="primary"] {
        background: linear-gradient(110deg, #00A85C 0%, #00D87A 25%, #5CFFB0 50%, #00D87A 75%, #00A85C 100%) !important;
        background-size: 320% 100% !important;
        background-position: 0% 50% !important;
        border: none !important;
        color: #FFFFFF !important;
        font-weight: 600 !important;
        letter-spacing: 0.10em !important;
        padding: 16px 56px !important;
        border-radius: 2px !important;
        box-shadow: var(--accent-glow), var(--shadow-soft) !important;
    }
    .stButton > button[kind="primary"]:hover {
        opacity: 1 !important;
    }
    .stButton > button[kind="primary"] p,
    .stButton > button[kind="primary"] span {
        color: #FFFFFF !important;
    }

    /* Ensure button label text stays white on dark background */
    .stButton > button p,
    .stButton > button span {
        color: white !important;
    }

    .stSelectbox > div > div {
        background: var(--grad-panel) !important;
        border: 1px solid var(--border) !important;
        color: var(--text-primary) !important;
        font-family: 'Inter', sans-serif !important;
        border-radius: 3px !important;
        box-shadow: var(--shadow-soft) !important;
        transition: border-color 0.25s var(--ease-out) !important;
    }
    .stSelectbox > div > div:hover {
        border-color: var(--accent) !important;
    }

    /* =========================================================
       Expanders (Learn More sections)
       ========================================================= */
    .stExpander {
        border: 1px solid var(--border-subtle) !important;
        border-left: 2px solid var(--border) !important;
        background: var(--grad-panel) !important;
        margin-bottom: 8px;
        border-radius: 4px !important;
        box-shadow: var(--shadow-soft) !important;
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
        margin: 48px auto;
        padding: 64px 56px;
        background: var(--grad-panel);
        border-radius: 6px;
        box-shadow: var(--shadow-lift);
        animation: rise-in 0.7s var(--ease-out) both;
        animation-delay: 0.20s;
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
        word-break: keep-all;
        overflow-wrap: normal;
        white-space: normal;
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


# Top-of-page anchor used for reliable scroll-to-top.
st.markdown('<div id="__page_top__" style="position:absolute;top:0;left:0;width:1px;height:1px;"></div>', unsafe_allow_html=True)

# Boot veil — once per session
if not st.session_state.get("_booted"):
    st.markdown("""
    <div id="boot-veil">
        <div class="wordmark">VOLATILITY</div>
        <div class="dot"></div>
    </div>
    """, unsafe_allow_html=True)
    st.session_state["_booted"] = True

# Always disable browser scroll restoration so Streamlit reruns don't bounce the user.
components.html("""
<script>
(function() {
    try {
        if (window.parent && window.parent.history && 'scrollRestoration' in window.parent.history) {
            window.parent.history.scrollRestoration = 'manual';
        }
    } catch (e) {}
})();
</script>
""", height=0)

# Post-onboarding: scroll to top and play a smooth fade-in
if st.session_state.pop("_just_onboarded", False):
    import time as _t
    _nonce = str(_t.time_ns())
    components.html(f"""
    <script>
    /* nonce={_nonce} */
    (function() {{
        var win = window.parent;
        var doc = win.document;
        function toTop() {{
            try {{ win.scrollTo(0, 0); }} catch (e) {{}}
            try {{ doc.documentElement.scrollTop = 0; doc.body.scrollTop = 0; }} catch (e) {{}}
            // Anchor at the top of the rendered page — scrollIntoView walks ancestors.
            var anchor = doc.getElementById('__page_top__');
            if (anchor && anchor.scrollIntoView) {{
                try {{ anchor.scrollIntoView({{ block: 'start', inline: 'start', behavior: 'auto' }}); }} catch (e) {{}}
            }}
            // Brute force: reset scrollTop on every scrollable element in the parent doc.
            var all = doc.querySelectorAll('*');
            for (var i = 0; i < all.length; i++) {{
                var el = all[i];
                if (el.scrollTop && el.scrollTop > 0) {{ el.scrollTop = 0; }}
            }}
        }}
        toTop();
        var ticks = 0;
        var iv = setInterval(function() {{
            toTop();
            ticks++;
            if (ticks > 60) clearInterval(iv);
        }}, 60);
        var app = doc.querySelector('.stApp');
        if (app) {{
            app.classList.add('post-onboard');
            setTimeout(function() {{ app.classList.remove('post-onboard'); }}, 900);
        }}
    }})();
    </script>
    """, height=0)


# Persistent JS: drive SCAN button pulse from real DOM events (click + spinner lifecycle).
components.html("""
<script>
(function() {
    var win = window.parent;
    var doc = win.document;
    if (win.__scanPulseHookedV3) return;
    if (win.__scanPulseHandler) {
        try { doc.removeEventListener('click', win.__scanPulseHandler, true); } catch (e) {}
    }
    win.__scanPulseHookedV3 = true;

    function findScanButton() {
        var btns = doc.querySelectorAll('.stButton button[kind="primary"]');
        for (var i = 0; i < btns.length; i++) {
            var t = (btns[i].innerText || '').trim().toUpperCase();
            if (t === 'SCAN') return btns[i];
        }
        return null;
    }

    function spinnerPresent() {
        return !!(doc.querySelector('[data-testid="stSpinner"]') || doc.querySelector('.stSpinner'));
    }

    win.__scanPulseHandler = function(e) {
        var btn = e.target.closest && e.target.closest('.stButton button[kind="primary"]');
        if (!btn) return;
        var label = (btn.innerText || '').trim().toUpperCase();
        if (label !== 'SCAN') return;
        doc.body.classList.add('scanning');
        btn.classList.add('clicked');
        setTimeout(function() {
            var b = findScanButton();
            if (b) b.classList.remove('clicked');
        }, 650);
        // Watch for the spinner to appear then disappear; clear the class when scan ends.
        var sawSpinner = false;
        var obs = new MutationObserver(function() {
            if (spinnerPresent()) { sawSpinner = true; return; }
            if (sawSpinner) {
                doc.body.classList.remove('scanning');
                obs.disconnect();
            }
        });
        obs.observe(doc.body, { childList: true, subtree: true });
        // Hard safety: drop the class after 30s no matter what.
        setTimeout(function() {
            doc.body.classList.remove('scanning');
            try { obs.disconnect(); } catch (_) {}
        }, 30000);
    };
    doc.addEventListener('click', win.__scanPulseHandler, true);
})();
</script>
""", height=0)


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
<div class="headline headline-lg" style="margin-bottom: 8px;">VOLATILITY TERMINAL</div>
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
        if st.button("START SCANNING", use_container_width=True, key="onboard_start"):
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
            st.session_state["_just_onboarded"] = True
            st.rerun()
            return True

    with col2:
        if st.button("JUST BROWSING", use_container_width=True, key="onboard_browse"):
            profile = UserProfile(
                budget=budget,
                risk_tolerance=risk.lower(),
                experience=experience,
                trading_mode="browsing",
            )
            profile.save()
            st.session_state["profile"] = profile
            st.session_state["_just_onboarded"] = True
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

@st.cache_data(ttl=300)
def _cached_polymarkets(limit: int = 10):
    from nasdaq_scanner.data.polymarket_client import fetch_top_markets
    return fetch_top_markets(limit=limit)


def _poly_esc(text: str) -> str:
    # &#36; keeps literal $ out of the markdown source — st.markdown treats
    # paired $...$ as LaTeX and mangles everything between them
    return (
        (text or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("$", "&#36;")
    )


def _poly_usd(v) -> str:
    v = v or 0
    if v >= 1_000_000_000:
        return f"&#36;{v/1_000_000_000:.1f}B"
    if v >= 1_000_000:
        return f"&#36;{v/1_000_000:.1f}M"
    if v >= 1_000:
        return f"&#36;{v/1_000:.0f}K"
    return f"&#36;{v:.0f}"


def _poly_date(end_date: str, fmt: str = "%b %d") -> str:
    if not end_date:
        return "—"
    try:
        return datetime.fromisoformat(end_date.replace("Z", "+00:00")).strftime(fmt).upper()
    except Exception:
        return "—"


def _poly_days_left(end_date: str):
    if not end_date:
        return None
    try:
        end = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
        return (end - datetime.now(end.tzinfo)).days
    except Exception:
        return None


def _poly_change_html(change: float, cls: str = "poly-num") -> str:
    pts = change * 100
    color = "poly-pos" if pts > 0.05 else "poly-neg" if pts < -0.05 else ""
    return f'<span class="{cls} {color}">{pts:+.1f}</span>'


def _poly_indication(m):
    """Heuristic trade read on a market. Returns (label, css_class, rationale).

    Reads are structural — favorite-longshot bias, yield-to-resolution,
    momentum, execution quality — not a view on the event itself.
    """
    yes = m.yes_price
    days = _poly_days_left(m.end_date)
    chg_pts = m.one_day_change * 100
    spread = m.spread
    thin = (spread is not None and spread >= 0.03) or (0 < m.liquidity < 10_000)

    if days is None:
        days_str = "an unknown horizon"
    elif days < 0:
        days_str = "an open-ended horizon (already past its listed close date)"
    elif days == 0:
        days_str = "under a day"
    else:
        days_str = f"{days} day{'s' if days != 1 else ''}"

    def cents(p: float) -> str:
        c = p * 100
        return f"{c:.1f}¢" if c < 10 else f"{c:.0f}¢"

    parts = []

    if yes >= 0.90:
        ret = (1 - yes) / yes * 100
        label, cls = "YES YIELD", "pos"
        parts.append(
            f"YES trades at {cents(yes)} — buying it returns {ret:.1f}% over {days_str} if the favorite holds. "
            f"Heavy favorites historically resolve YES slightly more often than their price implies "
            f"(favorite-longshot bias), but a single upset costs the entire stake. "
            f"Treat it as a yield position, not a lock, and size accordingly."
        )
    elif yes <= 0.10:
        no_ret = yes / (1 - yes) * 100
        if days is not None and 0 <= days <= 30 and no_ret >= 1.5:
            label, cls = "NO YIELD", "pos"
            parts.append(
                f"YES at {cents(yes)} is a lottery ticket, and longshots are chronically overpriced — "
                f"the value side is NO at {cents(1 - yes)}, returning {no_ret:.1f}% in {days_str} if nothing changes. "
                f"Small edge, total loss on a surprise."
            )
        else:
            label, cls = "PASS", "neutral"
            parts.append(
                f"YES at {cents(yes)} is a longshot — historically overpriced, so buying it is negative expected value. "
                f"The NO side yields under 2% over {days_str}, which rarely justifies locking up capital. "
                f"No structural edge on either side."
            )
    elif 0.40 <= yes <= 0.60:
        if days is not None and 0 <= days <= 2:
            label, cls = "EVENT RISK", "warn"
            parts.append(
                f"Near even odds ({yes*100:.0f}/{(1-yes)*100:.0f}) resolving in {days_str} — pure binary event risk. "
                f"Expect maximum volatility into close; any position here is a bet on the event, not on mispricing."
            )
        else:
            label, cls = "NO EDGE", "neutral"
            parts.append(
                "Priced as a coin flip — public information is already in the price. "
                "Trading here without genuine private insight just pays the spread to gamble. "
                "Skip unless you know something the market doesn't."
            )
    else:
        label, cls = "FAIR ZONE", "neutral"
        parts.append(
            f"Mid-range pricing ({yes*100:.0f}% YES) — outside the zones where structural biases bite. "
            f"Any edge here requires an actual view on the event; the price itself offers nothing to exploit."
        )

    if abs(chg_pts) >= 3:
        direction = "toward YES" if chg_pts > 0 else "toward NO"
        if label in ("NO EDGE", "FAIR ZONE"):
            label, cls = ("MOMENTUM ▲", "pos") if chg_pts > 0 else ("MOMENTUM ▼", "neg")
        parts.append(
            f"Moved {chg_pts:+.1f} pts in 24h on {_poly_usd(m.volume_24h)} of volume — the market is repricing {direction}. "
            f"News-driven moves often drift further, but entering right after a spike risks paying the extreme; "
            f"wait for a pullback or cut size."
        )

    if thin:
        sp = f"{spread*100:.1f}¢" if spread is not None else "wide"
        parts.append(
            f"Caution: execution quality is poor (spread {sp}, liquidity {_poly_usd(m.liquidity)}) — "
            f"market orders will leak the edge as slippage. Use limit orders or pass."
        )
        if cls == "pos":
            cls = "warn"

    return label, cls, " ".join(parts)


def _poly_tooltip_html(m, ind) -> str:
    desc = _poly_esc(m.description).strip() or "No description provided for this market."
    bid = f"{m.best_bid*100:.1f}¢" if m.best_bid is not None else "—"
    ask = f"{m.best_ask*100:.1f}¢" if m.best_ask is not None else "—"
    spread = f"{m.spread*100:.1f}¢" if m.spread is not None else "—"
    last = f"{m.last_trade*100:.1f}¢" if m.last_trade is not None else "—"
    closes_full = _poly_date(m.end_date, "%b %d, %Y")
    days = _poly_days_left(m.end_date)
    closes = f"{closes_full}" + (f" ({days}D)" if days is not None and days >= 0 else "")
    stats = [
        ("Total Volume", _poly_usd(m.volume)),
        ("Liquidity", _poly_usd(m.liquidity)),
        ("Best Bid", bid),
        ("Best Ask", ask),
        ("Spread", spread),
        ("Last Trade", last),
    ]
    stat_html = "".join(
        f'<div><div class="poly-tooltip-label">{label}</div>'
        f'<div class="poly-tooltip-value">{value}</div></div>'
        for label, value in stats
    )
    label, cls, rationale = ind
    return (
        f'<div class="poly-tooltip">'
        f'<div class="poly-tooltip-read"><span class="poly-badge {cls}">{label}</span>{rationale}</div>'
        f'<div class="poly-tooltip-grid">{stat_html}</div>'
        f'<div class="poly-tooltip-desc">{desc}</div>'
        f'<div class="poly-tooltip-hint">Closes {closes} &nbsp;·&nbsp; Click to view on Polymarket ↗</div>'
        f'</div>'
    )


def _poly_row_html(m, rank: int) -> str:
    q = _poly_esc(m.question)
    cat = _poly_esc(m.category)
    cat_html = f'<span class="poly-cat">{cat}</span>' if cat else ""
    ind = _poly_indication(m)
    return (
        f'<a class="poly-row" href="{m.url}" target="_blank" rel="noopener">'
        f'<span class="poly-rank">{rank:02d}</span>'
        f'<span><span class="poly-q">{q}</span>{cat_html}</span>'
        f'<span class="poly-num poly-yes">{m.yes_price*100:.0f}%</span>'
        f'<span class="poly-num poly-no">{m.no_price*100:.0f}%</span>'
        f'<span class="poly-num">{_poly_usd(m.volume_24h)}</span>'
        f'{_poly_change_html(m.one_day_change)}'
        f'<span class="poly-meta">{_poly_date(m.end_date)}</span>'
        f'<span><span class="poly-badge {ind[1]}">{ind[0]}</span></span>'
        f'{_poly_tooltip_html(m, ind)}'
        f'</a>'
    )


def render_polymarket_tab():
    markets = _cached_polymarkets(limit=10)
    if not markets:
        st.markdown(
            '<div class="empty-state">'
            '<div class="empty-state-text">NO MARKETS AVAILABLE</div>'
            '<div class="empty-state-sub">Polymarket is unreachable or returned no active markets</div>'
            '</div>',
            unsafe_allow_html=True,
        )
        return

    total_24h = sum(m.volume_24h for m in markets)
    total_liq = sum(m.liquidity for m in markets)
    mover = max(markets, key=lambda m: abs(m.one_day_change))
    closing_week = len([
        m for m in markets
        if (d := _poly_days_left(m.end_date)) is not None and 0 <= d <= 7
    ])

    st.markdown(f"""
    <div class="metric-grid">
        <div class="metric-card">
            <div class="metric-card-label">Top Markets Tracked</div>
            <div class="metric-card-value">{len(markets)}</div>
        </div>
        <div class="metric-card">
            <div class="metric-card-label">24H Volume (Top 10)</div>
            <div class="metric-card-value">{_poly_usd(total_24h)}</div>
        </div>
        <div class="metric-card">
            <div class="metric-card-label">Combined Liquidity</div>
            <div class="metric-card-value">{_poly_usd(total_liq)}</div>
        </div>
        <div class="metric-card">
            <div class="metric-card-label">Closing Within 7 Days</div>
            <div class="metric-card-value">{closing_week}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Hero — the single most-traded market of the day
    top = markets[0]
    top_cat = _poly_esc(top.category)
    top_cat_html = f'<div class="poly-hero-cat">{top_cat}</div>' if top_cat else ""
    top_label, top_cls, top_read = _poly_indication(top)
    st.markdown(f"""
    <a class="poly-hero" href="{top.url}" target="_blank" rel="noopener">
        <div class="poly-hero-label">MOST TRADED TODAY</div>
        <div class="poly-hero-grid">
            <div>
                {top_cat_html}
                <div class="poly-hero-q">{_poly_esc(top.question)}</div>
            </div>
            <div>
                <div class="poly-hero-stat-label">Yes / No</div>
                <div class="poly-hero-stat-value"><span class="poly-yes">{top.yes_price*100:.0f}%</span> <span style="color: var(--text-tertiary); font-size: 18px;">/ {top.no_price*100:.0f}%</span></div>
                <div class="poly-hero-sub">{_poly_change_html(top.one_day_change, "poly-hero-sub-num")} pts 24h</div>
            </div>
            <div>
                <div class="poly-hero-stat-label">24H Volume</div>
                <div class="poly-hero-stat-value">{_poly_usd(top.volume_24h)}</div>
                <div class="poly-hero-sub">{_poly_usd(top.volume)} lifetime</div>
            </div>
            <div>
                <div class="poly-hero-stat-label">Closes</div>
                <div class="poly-hero-stat-value" style="font-size: 20px;">{_poly_date(top.end_date)}</div>
                <div class="poly-hero-sub">{_poly_usd(top.liquidity)} liquidity</div>
            </div>
        </div>
        <div class="poly-hero-read"><span class="poly-badge {top_cls}">{top_label}</span>{top_read}</div>
    </a>
    """, unsafe_allow_html=True)

    biggest_move = f"{mover.one_day_change*100:+.1f} pts — {_poly_esc(mover.question)}"
    st.markdown(
        f'<div class="market-summary">Top 10 Polymarket trades of the day, ranked by 24-hour volume. '
        f'Biggest 24h move: {biggest_move}. '
        f'Hover any market for depth, spread, and context. Click to open on Polymarket.</div>',
        unsafe_allow_html=True,
    )

    head = (
        '<div class="poly-row-head">'
        '<span>#</span><span>Market</span><span>Yes</span><span>No</span>'
        '<span>24H Vol</span><span>24H Δ</span><span>Closes</span><span>Signal</span>'
        '</div>'
    )
    rows = "".join(_poly_row_html(m, i + 1) for i, m in enumerate(markets))
    st.markdown(f'{head}<div class="poly-rows">{rows}</div>', unsafe_allow_html=True)

    st.markdown(
        '<div class="body-light" style="font-size: 11px; color: var(--text-tertiary); margin-top: -8px;">'
        'Signals are heuristic reads on market structure — favorite-longshot bias, yield to resolution, '
        'momentum, and execution quality — not a view on the events themselves. Educational only, not '
        'financial advice. Any prediction-market position can go to zero.</div>',
        unsafe_allow_html=True,
    )


@st.fragment
def _scan_section(profile):
    now = datetime.now()
    # Controls
    col1, col2, col3 = st.columns([2, 2, 1])

    with col1:
        scan_size = st.selectbox(
            "SCAN UNIVERSE",
            ["TOP 20 NASDAQ", "TOP 50 NASDAQ", "FULL NASDAQ 100"],
            label_visibility="collapsed"
        )

    with col3:
        if st.button("SCAN", type="primary", use_container_width=True):
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

    # Tabs — Polymarket is the landing tab; the NASDAQ signals moved later
    tab_markets, tab2, tab3, tab1, tab4, tab5 = st.tabs(
        ["POLYMARKET", "SCREENER", "TRACKER", "NASDAQ", "DOCUMENTATION", "PROFILE"]
    )

    # ─── NASDAQ TAB (signals) ───
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
            st.markdown("""<div class="empty-state">
<div class="empty-state-text">NO DATA</div>
</div>""", unsafe_allow_html=True)
        else:
            st.markdown("""<div class="screener-legend">
<span class="neg">Red RSI</span> = overbought (may pull back) &nbsp;&middot;&nbsp;
<span class="pos">Green RSI</span> = oversold (may bounce) &nbsp;&middot;&nbsp;
Regime = how volatile the stock is acting compared to normal
</div>""", unsafe_allow_html=True)

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

            st.markdown(f"""<table class="data-table">
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
</table>""", unsafe_allow_html=True)

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

        st.markdown(f"""<div class="headline headline-sm" style="margin-bottom: 24px;">PREDICTION PERFORMANCE</div>
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
</div>""", unsafe_allow_html=True)

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

            st.markdown(f"""<table class="data-table">
<thead><tr><th>Signal Type</th><th>Total</th><th>Wins</th><th>Losses</th><th>Win Rate</th></tr></thead>
<tbody>{type_rows}</tbody>
</table>""", unsafe_allow_html=True)

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

                pred_rows += (
                    f'<tr>'
                    f'<td>{date_display}</td>'
                    f'<td style="font-weight: 600;">{pred.symbol}</td>'
                    f'<td>{pred.signal_type}</td>'
                    f'<td>${pred.entry_price:.2f}</td>'
                    f'<td>{outcome_display}</td>'
                    f'<td class="{profit_class}">{profit_display}</td>'
                    f'<td style="color: {status_color}; text-transform: uppercase;">{pred.status.value}</td>'
                    f'</tr>'
                )

            st.markdown(f"""<table class="data-table">
<thead><tr><th>Date</th><th>Symbol</th><th>Type</th><th>Entry</th><th>Outcome</th><th>P/L</th><th>Status</th></tr></thead>
<tbody>{pred_rows}</tbody>
</table>""", unsafe_allow_html=True)
        else:
            st.markdown("""<div class="empty-state">
<div class="empty-state-text">NO PREDICTIONS YET</div>
<div class="empty-state-sub">Predictions appear as signals are generated</div>
</div>""", unsafe_allow_html=True)

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

    # ─── POLYMARKET TAB (landing) ───
    with tab_markets:
        render_polymarket_tab()

    # ─── DOCUMENTATION TAB ───
    with tab4:
        st.markdown('<div class="headline headline-sm" style="margin-bottom: 20px;">SIGNAL TYPES</div>', unsafe_allow_html=True)
        st.markdown("""<table class="data-table">
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
</table>""", unsafe_allow_html=True)

        st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

        st.markdown('<div class="headline headline-sm" style="margin-bottom: 20px;">ENTRY TIMING</div>', unsafe_allow_html=True)
        st.markdown("""<table class="data-table">
<thead><tr><th>Signal</th><th>Window</th><th>Why This Time</th></tr></thead>
<tbody>
<tr><td>PUT (Strong)</td><td>10:00-10:30 AM</td><td>Morning buying often exhausts here — sellers step in after the initial rush</td></tr>
<tr><td>PUT (Moderate)</td><td>2:30-3:00 PM</td><td>Institutional profit-taking in the afternoon creates natural selling pressure</td></tr>
<tr><td>CALL (Strong)</td><td>9:45-10:15 AM</td><td>Opening panic tends to exhaust quickly — rebounds start within 30 minutes</td></tr>
<tr><td>CALL (Moderate)</td><td>3:00-3:30 PM</td><td>Short covering and momentum buying often accelerate before market close</td></tr>
<tr><td>HEDGE</td><td>11:30 AM-1:00 PM</td><td>Midday is quieter — tighter bid/ask spreads mean better prices for protection</td></tr>
</tbody>
</table>""", unsafe_allow_html=True)

        st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

        st.markdown('<div class="headline headline-sm" style="margin-bottom: 20px;">INDICATOR DEFINITIONS</div>', unsafe_allow_html=True)
        st.markdown("""<table class="data-table">
<thead><tr><th>Indicator</th><th>What It Measures</th><th>Key Levels</th></tr></thead>
<tbody>
<tr><td>RSI</td><td>Momentum — how aggressively the stock has been bought or sold over the last 14 days</td><td>Above 70 = overbought (may drop). Below 30 = oversold (may bounce)</td></tr>
<tr><td>ATR Percentile</td><td>How volatile the stock is compared to its own last 100 days of movement</td><td>Above 70% = elevated volatility. Above 90% = extreme</td></tr>
<tr><td>Historical Vol</td><td>How much the price typically swings per year, based on the last 20 days</td><td>Above 40% is considered high volatility</td></tr>
<tr><td>BB %B</td><td>Where the price sits within its normal range (Bollinger Bands)</td><td>Above 1.0 = above the range (bearish signal). Below 0.0 = below the range (bullish signal)</td></tr>
<tr><td>IV Rank</td><td>How expensive options are now compared to the last year</td><td>Above 50 = pricier than average. Below 30 = cheap (good time to buy options)</td></tr>
</tbody>
</table>""", unsafe_allow_html=True)

        st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

        st.markdown("""<div class="body-light" style="margin-top: 24px; font-size: 11px; color: var(--text-tertiary);">
This scanner provides analytical signals for informational and educational purposes only. It does not constitute financial advice.
Options trading involves substantial risk of loss. Past performance does not guarantee future results.
Conduct independent research and consider consulting a licensed financial advisor before making investment decisions.
</div>""", unsafe_allow_html=True)

    # ─── PROFILE TAB ───
    with tab5:
        # Personalized greeting based on experience
        exp_greeting = {
            "beginner": "Welcome — you're in the right place. This scanner will walk you through every signal step by step.",
            "intermediate": "Good to have you. You know the basics — we'll help you find opportunities and sharpen your edge.",
            "experienced": "Let's get to work. Your profile tunes the scanner to match your strategy.",
        }
        greeting = exp_greeting.get(profile.experience, exp_greeting["beginner"])

        st.markdown(f"""<div style="margin-bottom: 28px;">
<div class="headline headline-sm" style="margin-bottom: 4px;">YOUR PROFILE</div>
<div style="font-family: Inter, sans-serif; font-size: 14px; color: var(--text-secondary); line-height: 1.5;">{greeting}</div>
</div>""", unsafe_allow_html=True)

        # ── How Your Settings Work ──
        max_pos = profile.max_position_dollars
        pct_label = int(profile.max_position_pct * 100)

        # Dynamic insight based on current profile combo
        if profile.risk_tolerance == "conservative" and profile.budget <= 1000:
            style_insight = "You're keeping it tight — small positions on high-conviction signals only. This is how most successful traders started."
        elif profile.risk_tolerance == "aggressive" and profile.budget >= 5000:
            style_insight = "Big budget, high risk tolerance — you'll see larger position sizes and more signal types. Make sure you're comfortable with the downside on every trade."
        elif profile.risk_tolerance == "moderate":
            style_insight = "Balanced approach — you'll see a mix of conservative and opportunistic plays sized to your budget."
        elif profile.risk_tolerance == "conservative":
            style_insight = "Playing it safe — the scanner will prioritize smaller, higher-probability setups within your budget."
        else:
            style_insight = "Aggressive stance — you'll see the full range of signals with larger position sizing. Keep an eye on your total exposure."

        st.markdown(f"""<div style="background: white; border: 1px solid var(--border-subtle); padding: 20px 24px; margin-bottom: 24px;">
<div class="label" style="margin-bottom: 12px;">HOW YOUR SETTINGS SHAPE THE APP</div>
<div style="font-family: Inter, sans-serif; font-size: 13px; color: var(--text-secondary); line-height: 1.7;">
<div style="margin-bottom: 8px;"><strong style="color: var(--text-primary);">Budget ${profile.budget:,}</strong> — Signal cards will show position costs relative to your budget. You won't see trades you can't afford.</div>
<div style="margin-bottom: 8px;"><strong style="color: var(--text-primary);">{profile.risk_tolerance.title()} risk</strong> — Max {pct_label}% of budget per trade (${max_pos:,.0f}). {"Tighter limits protect you from oversized bets." if profile.risk_tolerance == "conservative" else "Balanced sizing gives room to profit without overexposing." if profile.risk_tolerance == "moderate" else "Larger positions mean bigger swings both ways."}</div>
<div style="margin-bottom: 8px;"><strong style="color: var(--text-primary);">{profile.experience.title()} level</strong> — {"Every signal includes plain-English explanations of what's happening and why." if profile.experience == "beginner" else "Explanations are available on demand — expand for details when you need them." if profile.experience == "intermediate" else "Full technical data visible by default. Explanations available if needed."}</div>
<div><strong style="color: var(--text-primary);">{profile.mode_label} mode</strong> — {"Browse signals and learn without any trading account. Positions are hypothetical." if not profile.is_connected else "Practice trades with simulated money. Same real data, zero financial risk." if profile.trading_mode == "paper" else "Live execution through Alpaca. Real money, real trades."}</div>
</div>
<div style="font-family: Inter, sans-serif; font-size: 13px; color: var(--text-primary); margin-top: 16px; padding-top: 12px; border-top: 1px solid var(--border-subtle); font-style: italic;">{style_insight}</div>
</div>""", unsafe_allow_html=True)

        # ── Settings ──
        st.markdown('<div class="label" style="margin-bottom: 16px;">SETTINGS</div>', unsafe_allow_html=True)

        prof_col1, prof_col2 = st.columns(2)

        with prof_col1:
            st.markdown('<div class="label" style="margin-bottom: 4px; font-size: 11px;">BUDGET</div>', unsafe_allow_html=True)
            new_budget = st.select_slider(
                "Budget",
                options=[500, 1000, 2500, 5000, 10000, 25000],
                value=profile.budget,
                format_func=lambda x: f"${x:,}",
                label_visibility="collapsed",
                key="prof_budget",
            )

            st.markdown('<div class="label" style="margin-top: 24px; margin-bottom: 4px; font-size: 11px;">RISK TOLERANCE</div>', unsafe_allow_html=True)
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
            st.markdown('<div class="label" style="margin-bottom: 4px; font-size: 11px;">EXPERIENCE LEVEL</div>', unsafe_allow_html=True)
            exp_map = {"beginner": 0, "intermediate": 1, "experienced": 2}
            exp_labels = ["Beginner", "Intermediate", "Experienced"]
            exp_desc = {
                "Beginner": "Full explanations on every signal. We'll teach as you go.",
                "Intermediate": "Key details visible, deeper explanations on demand.",
                "Experienced": "Data-forward view. Less hand-holding, more signal.",
            }
            new_exp = st.radio(
                "Experience",
                exp_labels,
                index=exp_map.get(profile.experience, 0),
                label_visibility="collapsed",
                key="prof_exp",
            )
            st.markdown(f'<div class="body-light" style="font-size: 12px; margin-top: -8px;">{exp_desc[new_exp]}</div>', unsafe_allow_html=True)

            st.markdown('<div class="label" style="margin-top: 24px; margin-bottom: 8px; font-size: 11px;">TRADING ACCOUNT</div>', unsafe_allow_html=True)
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
                st.markdown(f"""<div style="font-family: Inter, sans-serif; font-size: 13px; color: var(--text-secondary); margin-bottom: 12px; line-height: 1.5;">
No account connected. You're in <strong>browsing mode</strong> — you can explore all signals with hypothetical sizing.
To execute trades, connect an <a href="https://alpaca.markets" target="_blank" style="color: var(--text-primary);">Alpaca</a> account below.</div>""", unsafe_allow_html=True)
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

        # Profile snapshot card
        new_max_pos = new_budget * {"Conservative": 0.15, "Moderate": 0.30, "Aggressive": 0.50}[new_risk]
        st.markdown(f"""<div style="background: white; border: 1px solid var(--border-subtle); padding: 24px;">
<div class="label" style="margin-bottom: 16px;">AT A GLANCE</div>
<div style="display: grid; grid-template-columns: 1fr 1fr 1fr 1fr; gap: 16px;">
<div>
<div class="signal-data-label">BUDGET</div>
<div class="signal-data-value">${new_budget:,}</div>
</div>
<div>
<div class="signal-data-label">MAX POSITION</div>
<div class="signal-data-value">${new_max_pos:,.0f}</div>
</div>
<div>
<div class="signal-data-label">RISK</div>
<div class="signal-data-value" style="font-size: 16px;">{new_risk}</div>
</div>
<div>
<div class="signal-data-label">MODE</div>
<div class="signal-data-value" style="font-size: 16px;">{profile.mode_label if new_mode == profile.trading_mode else new_mode.upper()}</div>
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
    st.markdown("""<div class="footer">
<span class="footer-text">VOLATILITY TERMINAL v4.0</span>
<span class="footer-text">DATA SOURCE: YAHOO FINANCE / ALPACA MARKETS</span>
</div>""", unsafe_allow_html=True)


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
                <div class="headline headline-lg">VOLATILITY TERMINAL</div>
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


    _scan_section(profile)


def app():
    """Entry point — shows onboarding or main dashboard."""
    profile = get_profile()

    if profile is None:
        show_onboarding()
    else:
        main()


if __name__ == "__main__":
    app()
