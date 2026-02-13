"""Trading signal generator."""

import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional

from nasdaq_scanner.config.settings import Settings, settings
from nasdaq_scanner.indicators.options_greeks import OptionsGreeks
from nasdaq_scanner.scanner.stock_screener import ScreenedStock

logger = logging.getLogger(__name__)


class SignalType(Enum):
    """Types of trading signals."""

    PUT_OPPORTUNITY = "PUT"
    CALL_OPPORTUNITY = "CALL"
    HEDGE_SIGNAL = "HEDGE"
    VOLATILITY_PLAY = "VOLATILITY"


class SignalStrength(Enum):
    """Signal strength/confidence levels."""

    WEAK = 1
    MODERATE = 2
    STRONG = 3
    VERY_STRONG = 4
    EXTREME = 5


@dataclass
class TradingSignal:
    """Container for a trading signal."""

    symbol: str
    signal_type: SignalType
    strength: SignalStrength
    timestamp: datetime

    # Price levels
    current_price: float
    suggested_strike: Optional[float]
    entry_price: Optional[float]
    stop_loss: Optional[float]
    target_price: Optional[float]

    # Analysis
    rationale: str
    key_metrics: dict
    risk_reward_ratio: Optional[float]

    # Options specifics
    suggested_expiry_days: int = 30
    suggested_delta: float = -0.30

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "symbol": self.symbol,
            "signal_type": self.signal_type.value,
            "strength": self.strength.value,
            "strength_name": self.strength.name,
            "timestamp": self.timestamp.isoformat(),
            "current_price": self.current_price,
            "suggested_strike": self.suggested_strike,
            "entry_price": self.entry_price,
            "stop_loss": self.stop_loss,
            "target_price": self.target_price,
            "rationale": self.rationale,
            "key_metrics": self.key_metrics,
            "risk_reward_ratio": self.risk_reward_ratio,
            "suggested_expiry_days": self.suggested_expiry_days,
            "suggested_delta": self.suggested_delta,
        }


class SignalGenerator:
    """Generate trading signals from screened stocks."""

    def __init__(self, config: Optional[Settings] = None):
        """Initialize signal generator."""
        self.config = config or settings

    def generate_signals(
        self,
        screened_stocks: list[ScreenedStock],
        max_signals: int = 10,
    ) -> list[TradingSignal]:
        """
        Generate trading signals from screened stocks.

        Args:
            screened_stocks: List of pre-screened stocks
            max_signals: Maximum signals to return

        Returns:
            List of TradingSignal objects
        """
        signals = []

        for stock in screened_stocks:
            signal = self._analyze_for_signal(stock)
            if signal:
                signals.append(signal)

        # Sort by strength (descending) then by risk/reward
        signals.sort(
            key=lambda s: (s.strength.value, s.risk_reward_ratio or 0),
            reverse=True,
        )

        return signals[:max_signals]

    def _analyze_for_signal(self, stock: ScreenedStock) -> Optional[TradingSignal]:
        """Analyze a stock and generate appropriate signal if conditions met."""
        # Check for PUT opportunity (bearish signal)
        put_signal = self._check_put_opportunity(stock)
        if put_signal:
            return put_signal

        # Check for CALL opportunity (bullish signal)
        call_signal = self._check_call_opportunity(stock)
        if call_signal:
            return call_signal

        # Check for hedge signal
        hedge_signal = self._check_hedge_signal(stock)
        if hedge_signal:
            return hedge_signal

        # Check for pure volatility play
        vol_signal = self._check_volatility_play(stock)
        if vol_signal:
            return vol_signal

        return None

    def _check_put_opportunity(self, stock: ScreenedStock) -> Optional[TradingSignal]:
        """
        Check for PUT opportunity.

        Criteria:
        - RSI overbought (> 70)
        - High IV Rank (> 50)
        - Price above upper Bollinger Band or high BB %B
        - High ATR percentile
        """
        conditions_met = 0
        rationale_parts = []

        # RSI overbought
        if stock.rsi > self.config.rsi_overbought:
            conditions_met += 2
            rationale_parts.append(f"RSI overbought at {stock.rsi:.1f}")

        # IV Rank elevated
        if stock.iv_rank and stock.iv_rank > 50:
            conditions_met += 1
            rationale_parts.append(f"IV Rank elevated at {stock.iv_rank:.1f}")

        # Price above upper BB
        if stock.bb_pband > 1:
            conditions_met += 2
            rationale_parts.append("Price above upper Bollinger Band")
        elif stock.bb_pband > 0.8:
            conditions_met += 1
            rationale_parts.append("Price near upper Bollinger Band")

        # High volatility
        if stock.atr_percentile > 80:
            conditions_met += 1
            rationale_parts.append(f"High volatility (ATR %ile: {stock.atr_percentile:.0f})")

        # Need at least 3 conditions for a signal
        if conditions_met < 3:
            return None

        # Calculate suggested strike and levels
        suggested_strike = OptionsGreeks.suggest_strike_for_put(
            current_price=stock.current_price,
            target_delta=-0.30,
            volatility=stock.implied_volatility or stock.historical_volatility,
            days_to_expiry=30,
        )

        # Stop loss at price going 5% against
        stop_loss = stock.current_price * 1.05

        # Target: strike price (full profit)
        target_price = suggested_strike

        # Calculate risk/reward (simplified)
        risk = stop_loss - stock.current_price
        reward = stock.current_price - target_price
        rr_ratio = reward / risk if risk > 0 else 0

        strength = self._calculate_strength(conditions_met)

        return TradingSignal(
            symbol=stock.symbol,
            signal_type=SignalType.PUT_OPPORTUNITY,
            strength=strength,
            timestamp=datetime.now(),
            current_price=stock.current_price,
            suggested_strike=suggested_strike,
            entry_price=stock.current_price,
            stop_loss=round(stop_loss, 2),
            target_price=round(target_price, 2),
            rationale="; ".join(rationale_parts),
            key_metrics={
                "rsi": round(stock.rsi, 1),
                "iv_rank": round(stock.iv_rank, 1) if stock.iv_rank else None,
                "atr_percentile": round(stock.atr_percentile, 1),
                "bb_pband": round(stock.bb_pband, 2),
                "hv": round(stock.historical_volatility * 100, 1),
            },
            risk_reward_ratio=round(rr_ratio, 2),
            suggested_expiry_days=30,
            suggested_delta=-0.30,
        )

    def _check_call_opportunity(self, stock: ScreenedStock) -> Optional[TradingSignal]:
        """
        Check for CALL opportunity.

        Criteria:
        - RSI oversold (< 30)
        - High IV Rank (premium selling opportunity after bounce)
        - Price below lower Bollinger Band
        """
        conditions_met = 0
        rationale_parts = []

        # RSI oversold
        if stock.rsi < self.config.rsi_oversold:
            conditions_met += 2
            rationale_parts.append(f"RSI oversold at {stock.rsi:.1f}")

        # IV Rank elevated (good for selling puts = bullish)
        if stock.iv_rank and stock.iv_rank > 60:
            conditions_met += 1
            rationale_parts.append(f"IV Rank elevated at {stock.iv_rank:.1f}")

        # Price below lower BB
        if stock.bb_pband < 0:
            conditions_met += 2
            rationale_parts.append("Price below lower Bollinger Band")
        elif stock.bb_pband < 0.2:
            conditions_met += 1
            rationale_parts.append("Price near lower Bollinger Band")

        if conditions_met < 3:
            return None

        # For calls, suggest ATM or slightly OTM strike
        suggested_strike = round(stock.current_price * 1.02, 2)

        stop_loss = stock.current_price * 0.95
        target_price = stock.current_price * 1.10

        risk = stock.current_price - stop_loss
        reward = target_price - stock.current_price
        rr_ratio = reward / risk if risk > 0 else 0

        strength = self._calculate_strength(conditions_met)

        return TradingSignal(
            symbol=stock.symbol,
            signal_type=SignalType.CALL_OPPORTUNITY,
            strength=strength,
            timestamp=datetime.now(),
            current_price=stock.current_price,
            suggested_strike=suggested_strike,
            entry_price=stock.current_price,
            stop_loss=round(stop_loss, 2),
            target_price=round(target_price, 2),
            rationale="; ".join(rationale_parts),
            key_metrics={
                "rsi": round(stock.rsi, 1),
                "iv_rank": round(stock.iv_rank, 1) if stock.iv_rank else None,
                "atr_percentile": round(stock.atr_percentile, 1),
                "bb_pband": round(stock.bb_pband, 2),
            },
            risk_reward_ratio=round(rr_ratio, 2),
            suggested_expiry_days=45,
            suggested_delta=0.30,
        )

    def _check_hedge_signal(self, stock: ScreenedStock) -> Optional[TradingSignal]:
        """
        Check for HEDGE signal.

        Criteria:
        - Very high volatility regime
        - IV expanding rapidly
        - Good for portfolio protection
        """
        conditions_met = 0
        rationale_parts = []

        # Extreme volatility regime
        if stock.volatility_regime in ("high", "extreme"):
            conditions_met += 2
            rationale_parts.append(f"Volatility regime: {stock.volatility_regime}")

        # Very high IV rank
        if stock.iv_rank and stock.iv_rank > 80:
            conditions_met += 2
            rationale_parts.append(f"Very high IV Rank: {stock.iv_rank:.1f}")

        # High HV rank
        if stock.hv_rank > 80:
            conditions_met += 1
            rationale_parts.append(f"High HV Rank: {stock.hv_rank:.1f}")

        if conditions_met < 3:
            return None

        # Hedge: suggest deep OTM put
        suggested_strike = round(stock.current_price * 0.90, 2)

        strength = self._calculate_strength(conditions_met)

        return TradingSignal(
            symbol=stock.symbol,
            signal_type=SignalType.HEDGE_SIGNAL,
            strength=strength,
            timestamp=datetime.now(),
            current_price=stock.current_price,
            suggested_strike=suggested_strike,
            entry_price=None,  # Hedge, not a directional trade
            stop_loss=None,
            target_price=None,
            rationale=f"Hedge opportunity: {'; '.join(rationale_parts)}",
            key_metrics={
                "volatility_regime": stock.volatility_regime,
                "iv_rank": round(stock.iv_rank, 1) if stock.iv_rank else None,
                "hv_rank": round(stock.hv_rank, 1),
                "hv": round(stock.historical_volatility * 100, 1),
            },
            risk_reward_ratio=None,
            suggested_expiry_days=45,
            suggested_delta=-0.15,  # Deep OTM for hedges
        )

    def _check_volatility_play(self, stock: ScreenedStock) -> Optional[TradingSignal]:
        """
        Check for pure volatility play (straddle/strangle candidates).

        Criteria:
        - Very high ATR percentile
        - Low IV rank (cheap options relative to expected move)
        """
        conditions_met = 0
        rationale_parts = []

        # Very high realized volatility
        if stock.atr_percentile > 90:
            conditions_met += 2
            rationale_parts.append(f"Very high ATR percentile: {stock.atr_percentile:.0f}")

        # But relatively low IV (options cheap)
        if stock.iv_rank and stock.iv_rank < 30:
            conditions_met += 2
            rationale_parts.append(f"Low IV Rank: {stock.iv_rank:.1f} (options cheap)")

        # Wide BB (high volatility visible)
        if stock.bb_width > 10:
            conditions_met += 1
            rationale_parts.append(f"Wide Bollinger Bands: {stock.bb_width:.1f}%")

        if conditions_met < 3:
            return None

        strength = self._calculate_strength(conditions_met)

        return TradingSignal(
            symbol=stock.symbol,
            signal_type=SignalType.VOLATILITY_PLAY,
            strength=strength,
            timestamp=datetime.now(),
            current_price=stock.current_price,
            suggested_strike=stock.current_price,  # ATM for straddles
            entry_price=stock.current_price,
            stop_loss=None,
            target_price=None,
            rationale=f"Volatility play (straddle/strangle candidate): {'; '.join(rationale_parts)}",
            key_metrics={
                "atr_percentile": round(stock.atr_percentile, 1),
                "iv_rank": round(stock.iv_rank, 1) if stock.iv_rank else None,
                "bb_width": round(stock.bb_width, 2),
                "hv": round(stock.historical_volatility * 100, 1),
            },
            risk_reward_ratio=None,
            suggested_expiry_days=30,
            suggested_delta=0.50,  # ATM
        )

    def _calculate_strength(self, conditions_met: int) -> SignalStrength:
        """Calculate signal strength based on conditions met."""
        if conditions_met >= 7:
            return SignalStrength.EXTREME
        elif conditions_met >= 5:
            return SignalStrength.VERY_STRONG
        elif conditions_met >= 4:
            return SignalStrength.STRONG
        elif conditions_met >= 3:
            return SignalStrength.MODERATE
        else:
            return SignalStrength.WEAK
