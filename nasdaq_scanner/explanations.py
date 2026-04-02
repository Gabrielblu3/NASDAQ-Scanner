"""Educational explanation generator for trading signals and indicators.

All explanations are dynamically generated from actual computed values.
Language uses 'tends to', 'historically', 'often' — never 'will' or 'guaranteed'.
"""


def generate_signal_summary(signal) -> str:
    """Generate a plain-English 'What's happening' summary for a signal."""
    symbol = signal.symbol
    metrics = signal.key_metrics
    signal_type = signal.signal_type.value

    if signal_type == "PUT":
        parts = []
        rsi = metrics.get("rsi")
        bb = metrics.get("bb_pband")
        iv = metrics.get("iv_rank")
        atr = metrics.get("atr_percentile")

        if rsi and rsi > 70:
            parts.append(
                f"{symbol} has been climbing aggressively — its momentum score (RSI) "
                f"hit {rsi:.0f}, which means buyers have been pushing hard. "
                f"When stocks get this stretched above 70, they tend to cool off."
            )
        if bb and bb > 1.0:
            parts.append(
                "The price has broken above its normal trading range (Bollinger Band), "
                "which historically signals the move may be overdone."
            )
        elif bb and bb > 0.8:
            parts.append(
                "The price is near the top of its normal trading range, "
                "suggesting upside momentum may be fading."
            )
        if iv and iv > 50:
            parts.append(
                f"Options are priced higher than usual (IV Rank: {iv:.0f}), "
                "confirming the market expects a significant move."
            )
        if atr and atr > 80:
            parts.append(
                f"Volatility is elevated (ATR percentile: {atr:.0f}%), "
                "meaning daily price swings are larger than normal."
            )

        if parts:
            return " ".join(parts) + " This setup suggests a potential pullback — a put option could profit from a decline."
        return f"{symbol} is showing bearish technical signals that suggest a potential pullback."

    elif signal_type == "CALL":
        parts = []
        rsi = metrics.get("rsi")
        bb = metrics.get("bb_pband")
        iv = metrics.get("iv_rank")

        if rsi and rsi < 30:
            parts.append(
                f"{symbol} has been selling off hard — its momentum score (RSI) "
                f"dropped to {rsi:.0f}, well below the oversold threshold of 30. "
                f"When stocks get this beaten down, they often bounce back."
            )
        if bb and bb < 0:
            parts.append(
                "The price has fallen below its normal trading range (Bollinger Band), "
                "which historically signals the selling may be overdone."
            )
        elif bb and bb < 0.2:
            parts.append(
                "The price is near the bottom of its normal range, "
                "suggesting the selloff may be running out of steam."
            )
        if iv and iv > 60:
            parts.append(
                f"Options are expensive (IV Rank: {iv:.0f}), "
                "reflecting heightened fear — which often peaks right before a reversal."
            )

        if parts:
            return " ".join(parts) + " This setup suggests a potential bounce — a call option could profit from a recovery."
        return f"{symbol} is showing bullish technical signals that suggest a potential bounce."

    elif signal_type == "HEDGE":
        parts = []
        regime = metrics.get("volatility_regime", "")
        iv = metrics.get("iv_rank")
        hv = metrics.get("hv_rank")

        parts.append(
            f"{symbol} is in a {regime}-volatility environment, "
            "meaning price swings are unusually large."
        )
        if iv and iv > 80:
            parts.append(
                f"The options market is pricing in major risk (IV Rank: {iv:.0f}). "
            )
        if hv and hv > 80:
            parts.append(
                f"Historical volatility is also elevated (HV Rank: {hv:.0f}), "
                "confirming real price turbulence, not just fear."
            )
        parts.append(
            "A protective put acts like insurance — it limits your downside "
            "if you already own this stock or similar positions."
        )
        return " ".join(parts)

    elif signal_type == "VOLATILITY":
        parts = []
        atr = metrics.get("atr_percentile")
        iv = metrics.get("iv_rank")
        bb_w = metrics.get("bb_width")

        parts.append(
            f"{symbol} is moving a lot but options are relatively cheap."
        )
        if atr and atr > 90:
            parts.append(
                f"Daily price swings are in the top {100 - atr:.0f}% of the last 100 days."
            )
        if iv and iv < 30:
            parts.append(
                f"Yet options are cheap (IV Rank: {iv:.0f}), meaning the market "
                "hasn't caught up to the actual movement."
            )
        if bb_w and bb_w > 10:
            parts.append(
                f"Bollinger Band width is {bb_w:.1f}%, confirming wide price action."
            )
        parts.append(
            "A straddle (buying both a call and put at the same strike) profits "
            "from a big move in either direction. You don't need to pick which way — "
            "just that it moves."
        )
        return " ".join(parts)

    return ""


def generate_strike_explanation(signal) -> str:
    """Explain why a particular strike price was chosen."""
    if signal.signal_type.value == "PUT":
        return (
            f"The ${signal.suggested_strike:.2f} strike was chosen to target a delta of "
            f"{signal.suggested_delta:.2f}. Delta tells you how much the option's price moves "
            f"for every $1 change in the stock. A delta of {signal.suggested_delta:.2f} means "
            f"for every $1 {signal.symbol} drops, your put gains roughly "
            f"${abs(signal.suggested_delta):.2f}. This balances cost (cheaper than deep "
            f"in-the-money options) with meaningful profit potential."
        )
    elif signal.signal_type.value == "CALL":
        return (
            f"The ${signal.suggested_strike:.2f} strike is slightly above the current price "
            f"(about 2% out-of-the-money). This keeps the option affordable while giving you "
            f"solid profit potential if {signal.symbol} bounces. The target delta of "
            f"{signal.suggested_delta:.2f} means the option captures about {signal.suggested_delta:.0%} "
            f"of each $1 move upward."
        )
    elif signal.signal_type.value == "HEDGE":
        return (
            f"The ${signal.suggested_strike:.2f} strike is about 10% below the current price — "
            f"a deep out-of-the-money put. This is cheaper than closer strikes because it only "
            f"pays off on a significant drop. Think of it as catastrophe insurance: you pay a small "
            f"premium to protect against a large loss."
        )
    elif signal.signal_type.value == "VOLATILITY":
        return (
            f"The ${signal.suggested_strike:.2f} strike is at-the-money (matching the current price). "
            f"For a straddle, you want delta near 0.50 so you profit equally from moves up or down. "
            f"The cost is higher than a directional bet, but you don't need to guess the direction."
        )
    return ""


def format_greeks_educational(greeks) -> list[dict]:
    """Format Greeks with plain-English explanations. Returns list of dicts."""
    if not greeks:
        return []

    items = []

    items.append({
        "name": "Delta",
        "value": f"{greeks.delta:.2f}",
        "explanation": (
            f"For every $1 the stock moves, your option changes by ~${abs(greeks.delta):.2f}. "
            + ("Negative delta means you profit when the stock drops." if greeks.delta < 0
               else "Positive delta means you profit when the stock rises.")
        ),
    })

    items.append({
        "name": "Theta",
        "value": f"${greeks.theta:.2f}/day",
        "explanation": (
            f"Time decay — your option loses about ${abs(greeks.theta):.2f} in value each day, "
            "even if the stock doesn't move. The clock is always working against option buyers."
        ),
    })

    items.append({
        "name": "Vega",
        "value": f"${greeks.vega:.2f}",
        "explanation": (
            f"For every 1% increase in implied volatility (market fear), your option gains "
            f"~${greeks.vega:.2f}. If fear spikes, your option becomes more valuable."
        ),
    })

    items.append({
        "name": "Gamma",
        "value": f"{greeks.gamma:.4f}",
        "explanation": (
            "How fast delta changes as the stock moves. Higher gamma means delta accelerates "
            "— your option becomes more sensitive to price changes as it moves in your favor."
        ),
    })

    return items


def generate_strength_breakdown(signal) -> str:
    """Generate a breakdown of how the signal scored its strength."""
    scoring = getattr(signal, "scoring_breakdown", None)
    if not scoring:
        total = signal.strength.value
        return f"Signal strength: {signal.strength.name} ({total}/5)"

    lines = [f"Signal strength: {signal.strength.name}"]
    total_points = 0
    for item in scoring:
        lines.append(f"  + {item['points']}pt — {item['condition']} ({item['value']})")
        total_points += item["points"]
    lines.append(f"  Total: {total_points} points (need 3 minimum for a signal)")
    return "\n".join(lines)


def generate_market_summary(screened, signals) -> str:
    """Generate a dynamic plain-English summary of market conditions."""
    if not screened:
        return "No stocks passed the screening filters. The market may be in a low-volatility period."

    avg_rsi = sum(s.rsi for s in screened) / len(screened)
    overbought = len([s for s in screened if s.rsi > 70])
    oversold = len([s for s in screened if s.rsi < 30])
    high_vol = len([s for s in screened if s.volatility_regime in ("high", "extreme", "HIGH", "EXTREME")])

    parts = []

    # RSI context
    if avg_rsi > 60:
        parts.append(
            f"The average momentum across scanned stocks is {avg_rsi:.0f} (leaning overbought) — "
            "the market has been buying aggressively, which often precedes a cooldown."
        )
    elif avg_rsi < 40:
        parts.append(
            f"The average momentum is {avg_rsi:.0f} (oversold territory) — "
            "selling pressure has been heavy, which sometimes sets up bounce opportunities."
        )
    else:
        parts.append(
            f"The average momentum across scanned stocks is {avg_rsi:.0f} (neutral range)."
        )

    # Individual counts
    if overbought > 0:
        parts.append(
            f"{overbought} stock{'s are' if overbought != 1 else ' is'} overbought and could pull back."
        )
    if oversold > 0:
        parts.append(
            f"{oversold} stock{'s are' if oversold != 1 else ' is'} oversold and may be due for a bounce."
        )
    if high_vol > 0:
        parts.append(
            f"{high_vol} stock{'s show' if high_vol != 1 else ' shows'} elevated volatility — "
            "bigger price swings mean more opportunity, but also more risk."
        )

    return " ".join(parts)


def generate_risk_note(signal) -> str:
    """Generate a 'what could go wrong' note for a signal."""
    signal_type = signal.signal_type.value

    if signal_type == "PUT":
        stop = f"${signal.stop_loss:.2f}" if signal.stop_loss else "your defined level"
        return (
            f"Strong earnings, buybacks, or bullish sector news could push {signal.symbol} higher "
            f"despite overbought signals. Momentum can persist longer than expected. "
            f"Use the stop loss at {stop} to limit downside."
        )
    elif signal_type == "CALL":
        stop = f"${signal.stop_loss:.2f}" if signal.stop_loss else "your defined level"
        return (
            f"Continued negative sentiment, downgrades, or broad market weakness could push "
            f"{signal.symbol} lower despite oversold conditions. Oversold stocks can stay oversold. "
            f"Use the stop loss at {stop} to cap your risk."
        )
    elif signal_type == "HEDGE":
        return (
            f"If volatility subsides and {signal.symbol} stabilizes, the protective put "
            f"loses value over time (theta decay). Hedging has a cost — think of it as "
            f"an insurance premium you pay for peace of mind."
        )
    elif signal_type == "VOLATILITY":
        return (
            f"If {signal.symbol} stays flat and doesn't make a big move, both legs of the "
            f"straddle lose value to time decay. You need a move large enough to offset "
            f"the cost of buying two options. Low-volatility chop is the enemy of this strategy."
        )
    return ""


def generate_iv_explanation(iv_rank) -> str:
    """Explain what IV Rank means in context."""
    if iv_rank is None:
        return "IV Rank unavailable — options data not loaded for this stock."

    if iv_rank > 70:
        return (
            f"IV Rank: {iv_rank:.0f} — Options are significantly more expensive than usual. "
            "The market is pricing in a big move. This can be good for option sellers "
            "but means buyers are paying a premium."
        )
    elif iv_rank > 50:
        return (
            f"IV Rank: {iv_rank:.0f} — Options are moderately priced above their yearly average. "
            "The market expects some movement but isn't in panic mode."
        )
    elif iv_rank > 30:
        return (
            f"IV Rank: {iv_rank:.0f} — Options are near their average price for the year. "
            "No unusual fear or complacency in the market."
        )
    else:
        return (
            f"IV Rank: {iv_rank:.0f} — Options are cheap relative to their yearly range. "
            "The market is calm — good time to buy options if you expect a move."
        )
