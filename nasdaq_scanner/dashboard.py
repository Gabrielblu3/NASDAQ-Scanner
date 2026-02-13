#!/usr/bin/env python3
"""NASDAQ Volatility Scanner - Premium Terminal Dashboard"""

import sys
import random
from datetime import datetime, timedelta
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components
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

# =============================================================================
# PREMIUM CSS - High-end 2026 motion graphics
# =============================================================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;500;600;700&family=Inter:wght@300;400;500;600;700&display=swap');

    /* =========================================================
       CSS Custom Properties for animatable gradients
       ========================================================= */
    @property --glow-opacity {
        syntax: '<number>';
        initial-value: 0.4;
        inherits: false;
    }

    @property --border-angle {
        syntax: '<angle>';
        initial-value: 0deg;
        inherits: false;
    }

    @property --shimmer-x {
        syntax: '<percentage>';
        initial-value: -100%;
        inherits: false;
    }

    /* =========================================================
       Root Design Tokens
       ========================================================= */
    :root {
        --matrix-green: #00ff41;
        --matrix-green-dim: #00cc33;
        --matrix-green-dark: #003300;
        --oled-black: #000000;
        --surface: rgba(8, 8, 8, 0.85);
        --surface-solid: #080808;
        --surface-elevated: rgba(16, 16, 16, 0.9);
        --accent: #00e5ff;
        --accent-dim: rgba(0, 229, 255, 0.15);
        --text-primary: #f0f0f0;
        --text-secondary: #00ff41;
        --text-dim: #4a4a4a;
        --border: rgba(255, 255, 255, 0.06);
        --border-hover: rgba(255, 255, 255, 0.12);
        --negative: #ff2d55;
        --negative-dim: rgba(255, 45, 85, 0.12);
        --positive: #00ff41;
        --positive-dim: rgba(0, 255, 65, 0.12);
        --warning: #ffcc00;
        --warning-dim: rgba(255, 204, 0, 0.12);

        /* Premium easing curves */
        --ease-out-expo: cubic-bezier(0.16, 1, 0.3, 1);
        --ease-out-quart: cubic-bezier(0.25, 1, 0.5, 1);
        --ease-in-out-quint: cubic-bezier(0.83, 0, 0.17, 1);
        --spring: cubic-bezier(0.34, 1.56, 0.64, 1);
    }

    /* =========================================================
       Global Resets & Base
       ========================================================= */
    * {
        -webkit-font-smoothing: antialiased;
        -moz-osx-font-smoothing: grayscale;
        text-rendering: optimizeLegibility;
    }

    html {
        scroll-behavior: smooth;
    }

    @media (prefers-reduced-motion: reduce) {
        *, *::before, *::after {
            animation-duration: 0.01ms !important;
            animation-iteration-count: 1 !important;
            transition-duration: 0.01ms !important;
        }
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

    /* =========================================================
       Scanline Overlay - Ultra subtle CRT effect
       ========================================================= */
    .scanline-overlay {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        pointer-events: none;
        z-index: 9999;
        background: repeating-linear-gradient(
            0deg,
            transparent 0px,
            transparent 1px,
            rgba(0, 0, 0, 0.015) 1px,
            rgba(0, 0, 0, 0.015) 2px
        );
        mix-blend-mode: multiply;
    }

    /* =========================================================
       Matrix Rain - Refined, fewer columns, GPU-accelerated
       ========================================================= */
    @keyframes rain-fall {
        0% {
            transform: translate3d(0, -100%, 0) scaleY(0.8);
            opacity: 0;
        }
        3% {
            opacity: 1;
            transform: translate3d(0, -90%, 0) scaleY(1);
        }
        85% {
            opacity: 0.15;
        }
        100% {
            transform: translate3d(0, 2200px, 0) scaleY(1);
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
            rgba(0,0,0,0.25) 0%,
            rgba(0,0,0,0.08) 30%,
            rgba(0,0,0,0.02) 60%,
            rgba(0,0,0,0) 100%);
        -webkit-mask-image: linear-gradient(to bottom,
            rgba(0,0,0,0.25) 0%,
            rgba(0,0,0,0.08) 30%,
            rgba(0,0,0,0.02) 60%,
            rgba(0,0,0,0) 100%);
    }

    .rain-column {
        position: absolute;
        top: -200px;
        color: #00ff41;
        font-family: 'JetBrains Mono', monospace;
        font-size: 13px;
        line-height: 1.4;
        opacity: 0.08;
        animation: rain-fall linear infinite;
        white-space: pre;
        letter-spacing: 3px;
        text-shadow: 0 0 8px rgba(0, 255, 65, 0.3);
        will-change: transform, opacity;
        backface-visibility: hidden;
        filter: blur(0.3px);
    }

    .rain-column:nth-child(3n) {
        opacity: 0.12;
        text-shadow: 0 0 12px rgba(0, 255, 65, 0.4);
        filter: blur(0px);
    }

    .rain-column:nth-child(7n) {
        opacity: 0.06;
        font-size: 11px;
        filter: blur(0.5px);
    }

    /* =========================================================
       Entrance Animations - Staggered fade-in
       ========================================================= */
    @keyframes fadeInUp {
        from {
            opacity: 0;
            transform: translate3d(0, 12px, 0);
            filter: blur(4px);
        }
        to {
            opacity: 1;
            transform: translate3d(0, 0, 0);
            filter: blur(0px);
        }
    }

    @keyframes fadeIn {
        from { opacity: 0; }
        to { opacity: 1; }
    }

    @keyframes slideInLeft {
        from {
            opacity: 0;
            transform: translate3d(-8px, 0, 0);
        }
        to {
            opacity: 1;
            transform: translate3d(0, 0, 0);
        }
    }

    /* =========================================================
       Glitch Effect - Subtle chromatic aberration
       ========================================================= */
    @keyframes glitch-subtle {
        0%, 92%, 100% {
            text-shadow: 0 0 10px rgba(0, 255, 65, 0.4);
            transform: translate3d(0, 0, 0);
        }
        93% {
            text-shadow:
                -1px 0 rgba(255, 45, 85, 0.4),
                1px 0 rgba(0, 229, 255, 0.4),
                0 0 10px rgba(0, 255, 65, 0.4);
            transform: translate3d(0.5px, 0, 0);
        }
        94% {
            text-shadow:
                1px 0 rgba(255, 45, 85, 0.3),
                -1px 0 rgba(0, 229, 255, 0.3),
                0 0 10px rgba(0, 255, 65, 0.4);
            transform: translate3d(-0.5px, 0, 0);
        }
        95% {
            text-shadow:
                -0.5px 0.5px rgba(255, 45, 85, 0.2),
                0.5px -0.5px rgba(0, 229, 255, 0.2),
                0 0 10px rgba(0, 255, 65, 0.4);
            transform: translate3d(0, 0.5px, 0);
        }
        96% {
            text-shadow: 0 0 10px rgba(0, 255, 65, 0.4);
            transform: translate3d(0, 0, 0);
        }
    }

    /* Second glitch layer using clip-path */
    @keyframes glitch-clip {
        0%, 90%, 100% {
            clip-path: inset(0 0 0 0);
        }
        91% {
            clip-path: inset(20% 0 60% 0);
        }
        92% {
            clip-path: inset(60% 0 10% 0);
        }
        93% {
            clip-path: inset(40% 0 30% 0);
        }
        94% {
            clip-path: inset(0 0 0 0);
        }
    }

    /* =========================================================
       Ambient Glow / Breathing
       ========================================================= */
    @keyframes breathe {
        0%, 100% {
            box-shadow: 0 0 0 rgba(0, 255, 65, 0);
            border-color: rgba(0, 255, 65, 0.3);
        }
        50% {
            box-shadow: 0 0 20px rgba(0, 255, 65, 0.06), 0 0 40px rgba(0, 255, 65, 0.03);
            border-color: rgba(0, 255, 65, 0.5);
        }
    }

    @keyframes shimmer {
        0% { --shimmer-x: -100%; }
        100% { --shimmer-x: 200%; }
    }

    @keyframes borderGlow {
        0%, 100% { --border-angle: 0deg; }
        100% { --border-angle: 360deg; }
    }

    @keyframes pulse-dot {
        0%, 100% {
            box-shadow: 0 0 4px var(--positive), 0 0 8px var(--positive);
            transform: scale(1);
        }
        50% {
            box-shadow: 0 0 8px var(--positive), 0 0 16px var(--positive), 0 0 24px rgba(0, 255, 65, 0.2);
            transform: scale(1.15);
        }
    }

    @keyframes blink-smooth {
        0%, 45% { opacity: 1; }
        50%, 95% { opacity: 0; }
        100% { opacity: 1; }
    }

    /* =========================================================
       Number Shimmer Effect
       ========================================================= */
    .num-shimmer {
        position: relative;
        display: inline-block;
    }

    .num-shimmer::after {
        content: '';
        position: absolute;
        top: 0;
        left: var(--shimmer-x, -100%);
        width: 60%;
        height: 100%;
        background: linear-gradient(
            90deg,
            transparent 0%,
            rgba(255, 255, 255, 0.04) 40%,
            rgba(255, 255, 255, 0.08) 50%,
            rgba(255, 255, 255, 0.04) 60%,
            transparent 100%
        );
        animation: shimmer 6s ease-in-out infinite;
        pointer-events: none;
    }

    /* =========================================================
       Typography
       ========================================================= */
    h1, h2, h3, h4, h5, h6, p, span, div, label {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
        color: var(--text-primary) !important;
    }

    .mono {
        font-family: 'JetBrains Mono', 'SF Mono', monospace !important;
    }

    /* =========================================================
       Terminal Header
       ========================================================= */
    .terminal-header {
        border-bottom: 1px solid rgba(0, 255, 65, 0.2);
        padding-bottom: 24px;
        margin-bottom: 32px;
        animation: fadeIn 0.8s var(--ease-out-expo) both;
        position: relative;
    }

    .terminal-header::after {
        content: '';
        position: absolute;
        bottom: -1px;
        left: 0;
        right: 0;
        height: 1px;
        background: linear-gradient(90deg,
            transparent 0%,
            rgba(0, 255, 65, 0.6) 20%,
            rgba(0, 255, 65, 0.6) 80%,
            transparent 100%);
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
        text-shadow: 0 0 10px rgba(0, 255, 65, 0.4);
        animation: glitch-subtle 8s var(--ease-in-out-quint) infinite;
        will-change: transform, text-shadow;
        backface-visibility: hidden;
    }

    /* Chromatic aberration pseudo-layers */
    .terminal-title::before,
    .terminal-title::after {
        content: attr(data-text);
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        pointer-events: none;
    }

    .terminal-title::before {
        color: var(--negative);
        opacity: 0;
        animation: glitch-clip 8s linear infinite;
        animation-delay: -0.1s;
        transform: translate3d(-1px, 0, 0);
    }

    .terminal-title::after {
        color: var(--accent);
        opacity: 0;
        animation: glitch-clip 8s linear infinite;
        animation-delay: -0.15s;
        transform: translate3d(1px, 0, 0);
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
        animation: fadeIn 1s var(--ease-out-expo) 0.2s both;
    }

    .terminal-time {
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 13px;
        color: var(--matrix-green) !important;
        opacity: 0.8;
        transition: opacity 0.3s ease;
    }

    .cursor-blink::after {
        content: '_';
        animation: blink-smooth 1.2s ease-in-out infinite;
        color: var(--matrix-green);
    }

    /* =========================================================
       Metric Cards - Frosted glass with stagger
       ========================================================= */
    .metric-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 16px;
        margin-bottom: 32px;
    }

    .metric-card {
        background: var(--surface);
        backdrop-filter: blur(12px) saturate(120%);
        -webkit-backdrop-filter: blur(12px) saturate(120%);
        border: 1px solid var(--border);
        border-left: 3px solid rgba(0, 255, 65, 0.4);
        padding: 20px 24px;
        transition: all 0.4s var(--ease-out-expo);
        animation: fadeInUp 0.6s var(--ease-out-expo) both;
        position: relative;
        overflow: hidden;
    }

    .metric-card:nth-child(1) { animation-delay: 0.1s; }
    .metric-card:nth-child(2) { animation-delay: 0.15s; }
    .metric-card:nth-child(3) { animation-delay: 0.2s; }
    .metric-card:nth-child(4) { animation-delay: 0.25s; }

    .metric-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: -100%;
        width: 60%;
        height: 100%;
        background: linear-gradient(
            90deg,
            transparent,
            rgba(255, 255, 255, 0.02),
            transparent
        );
        transition: left 0.8s var(--ease-out-expo);
        pointer-events: none;
    }

    .metric-card:hover {
        border-color: var(--border-hover);
        border-left-color: rgba(0, 255, 65, 0.7);
        transform: translateY(-1px);
        box-shadow: 0 4px 24px rgba(0, 0, 0, 0.3);
    }

    .metric-card:hover::before {
        left: 120%;
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
        transition: color 0.3s ease;
    }

    /* =========================================================
       Signal Cards - Premium glass with animated borders
       ========================================================= */
    .signal-card {
        background: var(--surface);
        backdrop-filter: blur(16px) saturate(130%);
        -webkit-backdrop-filter: blur(16px) saturate(130%);
        border: 1px solid var(--border);
        margin-bottom: 24px;
        position: relative;
        overflow: hidden;
        animation: fadeInUp 0.5s var(--ease-out-expo) both;
        transition: all 0.4s var(--ease-out-expo);
    }

    .signal-card:hover {
        border-color: var(--border-hover);
        transform: translateY(-1px);
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
    }

    .signal-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        width: 3px;
        height: 100%;
        transition: width 0.4s var(--ease-out-expo), box-shadow 0.4s var(--ease-out-expo);
    }

    .signal-card:hover::before {
        width: 4px;
    }

    .signal-card.put::before {
        background: var(--negative);
        box-shadow: 0 0 12px rgba(255, 45, 85, 0.3);
    }
    .signal-card.call::before {
        background: var(--positive);
        box-shadow: 0 0 12px rgba(0, 255, 65, 0.3);
    }
    .signal-card.hedge::before {
        background: var(--warning);
        box-shadow: 0 0 12px rgba(255, 204, 0, 0.3);
    }

    .signal-card:hover.put::before { box-shadow: 0 0 20px rgba(255, 45, 85, 0.5); }
    .signal-card:hover.call::before { box-shadow: 0 0 20px rgba(0, 255, 65, 0.5); }
    .signal-card:hover.hedge::before { box-shadow: 0 0 20px rgba(255, 204, 0, 0.5); }

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
        transition: box-shadow 0.3s var(--ease-out-expo);
    }

    .signal-type.put {
        background: var(--negative);
        color: var(--oled-black);
        box-shadow: 0 0 8px rgba(255, 45, 85, 0.3);
    }
    .signal-type.call {
        background: var(--positive);
        color: var(--oled-black);
        box-shadow: 0 0 8px rgba(0, 255, 65, 0.3);
    }
    .signal-type.hedge {
        background: var(--warning);
        color: var(--oled-black);
        box-shadow: 0 0 8px rgba(255, 204, 0, 0.3);
    }

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
        opacity: 0.8;
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

    .signal-metric { text-align: left; }

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
        transition: color 0.3s ease;
    }

    .signal-metric-value.positive { color: var(--positive) !important; }
    .signal-metric-value.negative { color: var(--negative) !important; }
    .signal-metric-value.accent { color: var(--accent) !important; }

    /* =========================================================
       Timing Box - Breathing border glow
       ========================================================= */
    .timing-box {
        background: linear-gradient(135deg, rgba(16, 16, 16, 0.9) 0%, rgba(0, 20, 0, 0.6) 100%);
        backdrop-filter: blur(8px);
        -webkit-backdrop-filter: blur(8px);
        border: 1px solid rgba(0, 255, 65, 0.25);
        padding: 20px 24px;
        margin-top: 20px;
        position: relative;
        overflow: hidden;
        animation: breathe 6s ease-in-out infinite;
        transition: all 0.4s var(--ease-out-expo);
    }

    .timing-box:hover {
        border-color: rgba(0, 255, 65, 0.5);
    }

    .timing-box::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 1px;
        background: linear-gradient(90deg, transparent, rgba(0, 255, 65, 0.6), transparent);
    }

    .timing-label {
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 9px;
        font-weight: 700;
        letter-spacing: 3px;
        text-transform: uppercase;
        color: var(--matrix-green) !important;
        margin-bottom: 12px;
        opacity: 0.8;
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
        opacity: 0.9;
    }

    .timing-note {
        font-size: 11px;
        color: var(--text-dim) !important;
        margin-top: 12px;
        line-height: 1.5;
    }

    /* =========================================================
       Rationale
       ========================================================= */
    .signal-rationale {
        font-size: 12px;
        color: var(--text-dim) !important;
        line-height: 1.7;
        padding-top: 20px;
        border-top: 1px solid var(--border);
        letter-spacing: 0.3px;
    }

    /* =========================================================
       Data Table - Clean with smooth hover
       ========================================================= */
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
        border-bottom: 1px solid rgba(0, 255, 65, 0.2);
        background: var(--surface-solid);
    }

    .data-table td {
        padding: 14px 16px;
        border-bottom: 1px solid var(--border);
        color: var(--text-primary) !important;
        transition: all 0.2s ease;
    }

    .data-table tr {
        transition: all 0.25s var(--ease-out-expo);
    }

    .data-table tr:hover td {
        background: rgba(255, 255, 255, 0.02);
    }

    .data-table td.positive { color: var(--positive) !important; }
    .data-table td.negative { color: var(--negative) !important; }

    /* =========================================================
       Status Indicators
       ========================================================= */
    .status-dot {
        display: inline-block;
        width: 8px;
        height: 8px;
        border-radius: 50%;
        margin-right: 8px;
        transition: all 0.3s ease;
    }

    .status-dot.active {
        background: var(--positive);
        animation: pulse-dot 2.5s cubic-bezier(0.4, 0, 0.6, 1) infinite;
        will-change: box-shadow, transform;
    }

    /* =========================================================
       Buttons - Smooth glass transitions
       ========================================================= */
    .stButton > button {
        background: transparent !important;
        border: 1px solid rgba(0, 255, 65, 0.3) !important;
        color: var(--matrix-green) !important;
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 11px !important;
        font-weight: 600 !important;
        letter-spacing: 2px !important;
        text-transform: uppercase !important;
        padding: 12px 32px !important;
        transition: all 0.35s var(--ease-out-expo) !important;
        will-change: background, color, box-shadow, border-color;
        position: relative;
        overflow: hidden;
    }

    .stButton > button:hover {
        background: rgba(0, 255, 65, 0.08) !important;
        border-color: rgba(0, 255, 65, 0.6) !important;
        color: var(--matrix-green) !important;
        box-shadow: 0 0 20px rgba(0, 255, 65, 0.15), 0 0 40px rgba(0, 255, 65, 0.05) !important;
    }

    .stButton > button:active {
        transform: scale(0.98) !important;
        transition: transform 0.1s ease !important;
    }

    /* =========================================================
       Select Box
       ========================================================= */
    .stSelectbox > div > div {
        background: var(--surface-solid) !important;
        border: 1px solid var(--border) !important;
        color: var(--text-primary) !important;
        font-family: 'JetBrains Mono', monospace !important;
        transition: border-color 0.3s ease !important;
    }

    .stSelectbox > div > div:hover {
        border-color: var(--border-hover) !important;
    }

    /* Hide streamlit branding */
    #MainMenu, footer, header { visibility: hidden; }

    /* =========================================================
       Tabs - Clean with smooth indicator
       ========================================================= */
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
        transition: color 0.3s var(--ease-out-expo) !important;
    }

    .stTabs [data-baseweb="tab"]:hover {
        color: rgba(0, 255, 65, 0.6) !important;
    }

    .stTabs [aria-selected="true"] {
        color: var(--matrix-green) !important;
        border-bottom: 2px solid var(--matrix-green) !important;
        text-shadow: 0 0 8px rgba(0, 255, 65, 0.2);
    }

    /* =========================================================
       Section Dividers
       ========================================================= */
    .section-divider {
        height: 1px;
        background: linear-gradient(90deg,
            transparent,
            rgba(0, 255, 65, 0.15),
            transparent);
        margin: 40px 0;
    }

    /* =========================================================
       Action Box
       ========================================================= */
    .action-box {
        background: rgba(0, 229, 255, 0.03);
        border: 1px solid rgba(0, 229, 255, 0.15);
        padding: 16px 20px;
        margin-top: 16px;
        transition: all 0.3s var(--ease-out-expo);
    }

    .action-box:hover {
        border-color: rgba(0, 229, 255, 0.3);
        background: rgba(0, 229, 255, 0.05);
    }

    .action-label {
        font-size: 9px;
        font-weight: 700;
        letter-spacing: 2px;
        text-transform: uppercase;
        color: var(--accent) !important;
        margin-bottom: 8px;
        opacity: 0.8;
    }

    .action-text {
        font-size: 13px;
        color: var(--text-primary) !important;
        line-height: 1.5;
    }

    /* =========================================================
       Hero Panel - Premium with animated top glow
       ========================================================= */
    @keyframes hero-glow {
        0%, 100% {
            box-shadow: 0 -2px 20px rgba(0, 255, 65, 0.1);
        }
        50% {
            box-shadow: 0 -2px 30px rgba(0, 255, 65, 0.2), 0 -2px 60px rgba(0, 255, 65, 0.05);
        }
    }

    .hero-panel {
        background: linear-gradient(180deg, rgba(0, 20, 0, 0.6) 0%, var(--oled-black) 100%);
        border: 1px solid rgba(0, 255, 65, 0.2);
        padding: 0;
        margin-bottom: 32px;
        position: relative;
        overflow: hidden;
        animation: fadeInUp 0.7s var(--ease-out-expo) 0.1s both,
                   hero-glow 6s ease-in-out infinite;
        transition: all 0.4s var(--ease-out-expo);
    }

    .hero-panel:hover {
        border-color: rgba(0, 255, 65, 0.4);
    }

    .hero-panel::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 2px;
        background: linear-gradient(90deg,
            transparent 0%,
            rgba(0, 255, 65, 0.4) 20%,
            var(--matrix-green) 50%,
            rgba(0, 255, 65, 0.4) 80%,
            transparent 100%);
        box-shadow: 0 0 15px rgba(0, 255, 65, 0.4);
    }

    /* Ambient light sweep on hero */
    .hero-panel::after {
        content: '';
        position: absolute;
        top: 0;
        left: -100%;
        width: 50%;
        height: 100%;
        background: linear-gradient(
            90deg,
            transparent,
            rgba(0, 255, 65, 0.015),
            transparent
        );
        animation: shimmer 8s ease-in-out infinite;
        pointer-events: none;
    }

    .hero-label {
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 9px;
        font-weight: 700;
        letter-spacing: 4px;
        color: var(--matrix-green) !important;
        padding: 16px 24px 8px 24px;
        border-bottom: 1px solid var(--border);
        background: rgba(0, 255, 65, 0.02);
        opacity: 0.7;
    }

    .hero-content {
        display: grid;
        grid-template-columns: 1fr 1fr 1fr;
        gap: 0;
        position: relative;
        z-index: 1;
    }

    .hero-main {
        padding: 24px 32px;
        border-right: 1px solid var(--border);
        animation: slideInLeft 0.6s var(--ease-out-expo) 0.3s both;
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

    .hero-signal-type.put {
        background: var(--negative);
        color: var(--oled-black);
        box-shadow: 0 0 12px rgba(255, 45, 85, 0.3);
    }
    .hero-signal-type.call {
        background: var(--positive);
        color: var(--oled-black);
        box-shadow: 0 0 12px rgba(0, 255, 65, 0.3);
    }
    .hero-signal-type.hedge {
        background: var(--warning);
        color: var(--oled-black);
        box-shadow: 0 0 12px rgba(255, 204, 0, 0.3);
    }

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
        animation: fadeInUp 0.6s var(--ease-out-expo) 0.4s both;
    }

    .hero-timing-label {
        font-size: 9px;
        font-weight: 700;
        letter-spacing: 2px;
        color: var(--matrix-green) !important;
        margin-bottom: 8px;
        opacity: 0.7;
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
        opacity: 0.8;
    }

    .hero-right {
        padding: 24px 32px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        animation: fadeInUp 0.6s var(--ease-out-expo) 0.5s both;
    }

    .hero-action-label {
        font-size: 9px;
        font-weight: 700;
        letter-spacing: 2px;
        color: var(--accent) !important;
        margin-bottom: 8px;
        opacity: 0.7;
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
        text-shadow: 0 0 8px rgba(0, 229, 255, 0.2);
    }

    /* =========================================================
       Market Overview Strip
       ========================================================= */
    .market-strip {
        display: grid;
        grid-template-columns: repeat(6, 1fr);
        gap: 0;
        background: var(--surface);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: 1px solid var(--border);
        margin-bottom: 24px;
        animation: fadeInUp 0.6s var(--ease-out-expo) 0.2s both;
    }

    .market-strip-item {
        padding: 16px 20px;
        border-right: 1px solid var(--border);
        text-align: center;
        transition: background 0.3s var(--ease-out-expo);
    }

    .market-strip-item:last-child {
        border-right: none;
    }

    .market-strip-item:hover {
        background: rgba(255, 255, 255, 0.015);
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
        transition: color 0.3s ease;
    }

    .market-strip-value.positive { color: var(--positive) !important; }
    .market-strip-value.negative { color: var(--negative) !important; }
    .market-strip-value.warning { color: var(--warning) !important; }
    .market-strip-value.accent { color: var(--accent) !important; }

    /* =========================================================
       No Signal State
       ========================================================= */
    .no-signal-hero {
        padding: 40px;
        text-align: center;
    }

    @keyframes scan-line {
        0% { transform: translateX(-100%); }
        100% { transform: translateX(300%); }
    }

    .no-signal-text {
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 14px;
        color: var(--text-dim) !important;
        letter-spacing: 2px;
        position: relative;
    }

    .no-signal-text::after {
        content: '';
        position: absolute;
        bottom: -4px;
        left: 0;
        width: 30%;
        height: 1px;
        background: var(--matrix-green);
        animation: scan-line 3s var(--ease-in-out-quint) infinite;
    }

    /* =========================================================
       Live Number Jitter Containers
       ========================================================= */
    .jitter-value {
        display: inline-block;
        font-variant-numeric: tabular-nums;
        transition: transform 0.1s ease;
    }

    /* =========================================================
       Noise texture overlay (ultra-subtle)
       ========================================================= */
    .noise-overlay {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        pointer-events: none;
        z-index: 9998;
        opacity: 0.015;
        background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");
        background-repeat: repeat;
        background-size: 256px 256px;
    }
</style>
""", unsafe_allow_html=True)


# Subtle overlays (no script tags in st.markdown — Streamlit strips them)
st.markdown("""
<div class="scanline-overlay"></div>
<div class="noise-overlay"></div>
""", unsafe_allow_html=True)

# JavaScript via components.html — this is the only way to run JS in Streamlit
components.html("""
<script>
(function() {
    'use strict';
    var parent = window.parent.document;

    // ---- Live Clock ----
    function updateClock() {
        var el = parent.getElementById('live-clock');
        if (!el) return;
        var now = new Date();
        var h = String(now.getHours()).padStart(2, '0');
        var m = String(now.getMinutes()).padStart(2, '0');
        var s = String(now.getSeconds()).padStart(2, '0');
        el.textContent = h + ':' + m + ':' + s;
    }

    // ---- Subtle Number Jitter ----
    function jitterNumbers() {
        var els = parent.querySelectorAll('.jitter-value');
        els.forEach(function(el) {
            var base = parseFloat(el.getAttribute('data-base'));
            if (isNaN(base)) return;
            var jitter = (Math.random() - 0.5) * 0.04;
            var val = base + jitter;
            el.textContent = '$' + val.toFixed(2);
        });
    }

    // ---- Smooth Counter Animation ----
    function animateCounters() {
        var counters = parent.querySelectorAll('.animate-count');
        counters.forEach(function(el) {
            if (el.getAttribute('data-animated') === 'true') return;
            el.setAttribute('data-animated', 'true');
            var target = parseInt(el.getAttribute('data-target'), 10);
            if (isNaN(target) || target === 0) return;
            var duration = 1200;
            var startTime = performance.now();

            function step(currentTime) {
                var elapsed = currentTime - startTime;
                var progress = Math.min(elapsed / duration, 1);
                var eased = progress === 1 ? 1 : 1 - Math.pow(2, -10 * progress);
                var current = Math.round(target * eased);
                el.textContent = current;
                if (progress < 1) {
                    requestAnimationFrame(step);
                }
            }
            requestAnimationFrame(step);
        });
    }

    // ---- Init ----
    function init() {
        setInterval(updateClock, 1000);
        updateClock();
        setInterval(jitterNumbers, 2500);
        setTimeout(animateCounters, 300);
    }

    setTimeout(init, 500);
})();
</script>
""", height=0)


# =============================================================================
# Helper Functions
# =============================================================================

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

    next_window = get_next_window_time(now, window)

    return {
        "window": window,
        "rationale": rationale,
        "action": action,
        "next": next_window
    }


def get_next_window_time(now, window):
    """Determine when the next entry window occurs."""
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


# =============================================================================
# Main Dashboard
# =============================================================================

def main():
    # Matrix Rain Background - refined, fewer columns
    rain_columns = ""
    matrix_chars = "0123456789"

    for i in range(35):
        left = i * 2.9
        duration = random.uniform(50, 120)
        delay = random.uniform(0, 60)
        text = "".join([random.choice(matrix_chars) + "\n" for _ in range(40)])
        rain_columns += f'<div class="rain-column" style="left:{left}%;animation-duration:{duration}s;animation-delay:-{delay}s;">{text}</div>'

    st.markdown(f'<div class="matrix-rain-container">{rain_columns}</div>', unsafe_allow_html=True)

    # Header
    now = datetime.now()
    market_status = "MARKET OPEN" if (9 <= now.hour < 16 and now.weekday() < 5) else "MARKET CLOSED"

    st.markdown(f"""
    <div class="terminal-header">
        <div style="display: flex; justify-content: space-between; align-items: flex-start;">
            <div>
                <h1 class="terminal-title" data-text="VOLATILITY TERMINAL">VOLATILITY TERMINAL</h1>
                <p class="terminal-subtitle">NASDAQ OPTIONS SIGNAL DETECTION</p>
            </div>
            <div style="text-align: right;">
                <p class="terminal-time">{now.strftime("%Y.%m.%d")}</p>
                <p class="terminal-time cursor-blink"><span id="live-clock">{now.strftime("%H:%M:%S")}</span> ET</p>
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

    # Metrics with animated counters
    strong_signals = len([s for s in signals if s.strength.value >= 4])

    st.markdown(f"""
    <div class="metric-grid">
        <div class="metric-card">
            <div class="metric-label">Symbols Scanned</div>
            <div class="metric-value"><span class="animate-count" data-target="{len(symbols)}">{len(symbols)}</span></div>
        </div>
        <div class="metric-card">
            <div class="metric-label">Passed Filters</div>
            <div class="metric-value"><span class="animate-count" data-target="{len(screened)}">{len(screened)}</span></div>
        </div>
        <div class="metric-card">
            <div class="metric-label">Active Signals</div>
            <div class="metric-value"><span class="animate-count" data-target="{len(signals)}">{len(signals)}</span></div>
        </div>
        <div class="metric-card">
            <div class="metric-label">Strong Signals</div>
            <div class="metric-value"><span class="animate-count" data-target="{strong_signals}">{strong_signals}</span></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # PRIMARY SIGNAL HERO PANEL
    put_signals = [s for s in signals if s.signal_type == SignalType.PUT_OPPORTUNITY]
    strong_puts = [s for s in put_signals if s.strength.value >= 4]

    if strong_puts:
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
                    <div class="hero-price"><span class="jitter-value" data-base="{primary.current_price:.2f}">${primary.current_price:.2f}</span></div>
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
                    <div class="hero-price"><span class="jitter-value" data-base="{primary.current_price:.2f}">${primary.current_price:.2f}</span></div>
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
            for idx, signal in enumerate(signals):
                signal_class = {
                    SignalType.PUT_OPPORTUNITY: "put",
                    SignalType.CALL_OPPORTUNITY: "call",
                    SignalType.HEDGE_SIGNAL: "hedge",
                    SignalType.VOLATILITY_PLAY: "hedge"
                }.get(signal.signal_type, "hedge")

                timing = get_optimal_entry_time(signal)

                price_str = f'<span class="jitter-value" data-base="{signal.current_price:.2f}">${signal.current_price:.2f}</span>' if signal.current_price else "-"
                strike_str = f"${signal.suggested_strike:.2f}" if signal.suggested_strike else None
                stop_str = f"${signal.stop_loss:.2f}" if signal.stop_loss else None
                target_str = f"${signal.target_price:.2f}" if signal.target_price else None
                rr_str = f"{signal.risk_reward_ratio:.1f}:1" if signal.risk_reward_ratio else None

                # Stagger animation delay
                delay = 0.05 * idx

                signal_html = f'''<div class="signal-card {signal_class}" style="animation-delay: {delay}s;">
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

        st.markdown(f"""
        <h3 style="font-family: 'JetBrains Mono', monospace; font-size: 14px; color: #00ff41 !important;
                   letter-spacing: 3px; margin: 0 0 24px 0; font-weight: 600;">
            PREDICTION PERFORMANCE
        </h3>

        <div class="metric-grid">
            <div class="metric-card">
                <div class="metric-label">Total Predictions</div>
                <div class="metric-value"><span class="animate-count" data-target="{stats['total_predictions']}">{stats['total_predictions']}</span></div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Win Rate</div>
                <div class="metric-value" style="color: {'#00ff41' if stats['win_rate'] >= 50 else '#ff2d55'} !important;">{stats['win_rate']:.1f}%</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Wins / Losses</div>
                <div class="metric-value"><span style="color: #00ff41;">{stats['wins']}</span> / <span style="color: #ff2d55;">{stats['losses']}</span></div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Pending</div>
                <div class="metric-value" style="color: #00e5ff !important;">{stats['pending']}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

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

        if stats['by_signal_type']:
            st.markdown("""
            <h3 style="font-family: 'JetBrains Mono', monospace; font-size: 12px; color: #00ff41 !important;
                       letter-spacing: 2px; margin: 24px 0 16px 0; font-weight: 600;">
                BY SIGNAL TYPE
            </h3>
            """, unsafe_allow_html=True)

            type_rows = ""
            for sig_type, data in stats['by_signal_type'].items():
                color = "#ff2d55" if "PUT" in sig_type else "#00ff41" if "CALL" in sig_type else "#ffcc00"
                type_rows += f"""
                <tr>
                    <td style="color: {color}; font-weight: 600;">{sig_type}</td>
                    <td>{data['total']}</td>
                    <td class="positive">{data['wins']}</td>
                    <td class="negative">{data['losses']}</td>
                    <td style="color: {'#00ff41' if data['win_rate'] >= 50 else '#ff2d55'};">{data['win_rate']:.1f}%</td>
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
                    PredictionStatus.LOSS: "#ff2d55",
                    PredictionStatus.PENDING: "#00e5ff",
                    PredictionStatus.EXPIRED: "#4a4a4a",
                    PredictionStatus.CANCELLED: "#4a4a4a"
                }.get(pred.status, "#ffffff")

                signal_color = "#ff2d55" if "PUT" in pred.signal_type else "#00ff41" if "CALL" in pred.signal_type else "#ffcc00"

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
        doc_signal_types = '''<h3 style="font-family: 'JetBrains Mono', monospace; font-size: 14px; color: #00ff41 !important; letter-spacing: 3px; margin: 32px 0 20px 0; font-weight: 600;">SIGNAL TYPES</h3>
<table class="data-table">
<thead><tr><th>Type</th><th>Trigger Conditions</th><th>Action</th></tr></thead>
<tbody>
<tr><td style="color: #ff2d55; font-weight: 600;">PUT</td><td>RSI above 70, price above upper Bollinger Band, elevated ATR</td><td>Buy put options, anticipate mean reversion</td></tr>
<tr><td style="color: #00ff41; font-weight: 600;">CALL</td><td>RSI below 30, price below lower Bollinger Band</td><td>Buy call options, anticipate oversold bounce</td></tr>
<tr><td style="color: #ffcc00; font-weight: 600;">HEDGE</td><td>Volatility regime HIGH or EXTREME, HV rank above 80</td><td>Buy protective puts on existing positions</td></tr>
</tbody>
</table>'''
        st.markdown(doc_signal_types, unsafe_allow_html=True)

        st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

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

        doc_disclaimer = '''<p style="font-size: 10px; color: #4a4a4a; letter-spacing: 1px; line-height: 2; margin-top: 40px;">
This terminal provides analytical signals for informational purposes only and does not constitute financial advice. Options trading involves substantial risk of loss. Past performance does not guarantee future results. Conduct independent research and consider consulting a licensed financial advisor before making investment decisions.
</p>'''
        st.markdown(doc_disclaimer, unsafe_allow_html=True)

    # Footer
    st.markdown(f"""
    <div class="section-divider"></div>
    <div style="display: flex; justify-content: space-between; align-items: center; padding: 16px 0; animation: fadeIn 1s var(--ease-out-expo) 0.8s both;">
        <span style="font-family: 'JetBrains Mono', monospace; font-size: 9px; color: #1a1a1a; letter-spacing: 2px;">
            VOLATILITY TERMINAL v3.0
        </span>
        <span style="font-family: 'JetBrains Mono', monospace; font-size: 9px; color: #1a1a1a; letter-spacing: 2px;">
            DATA SOURCE: ALPACA MARKETS API
        </span>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
