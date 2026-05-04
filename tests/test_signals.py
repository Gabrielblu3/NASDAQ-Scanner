"""Tests for the SignalGenerator with mock data."""

from unittest.mock import patch

import pytest

from nasdaq_scanner.config.settings import Settings
from nasdaq_scanner.scanner.signal_generator import (
    SignalGenerator,
    SignalStrength,
    SignalType,
    TradingSignal,
)
from nasdaq_scanner.scanner.stock_screener import ScreenedStock


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_screened_stock(**overrides) -> ScreenedStock:
    """Create a ScreenedStock with sensible defaults; override any field."""
    defaults = dict(
        symbol="TEST",
        current_price=150.0,
        change_pct=1.5,
        rsi=50.0,
        atr_percent=3.0,
        atr_percentile=75.0,
        bb_width=5.0,
        bb_pband=0.5,
        historical_volatility=0.30,
        hv_rank=50.0,
        volatility_regime="normal",
        implied_volatility=0.35,
        iv_rank=55.0,
        iv_percentile=60.0,
        put_call_ratio=0.9,
        market_cap=50_000_000_000,
        avg_volume=5_000_000,
        volume_ratio=1.2,
    )
    defaults.update(overrides)
    return ScreenedStock(**defaults)


def _make_put_stock(**extra) -> ScreenedStock:
    """Stock that should trigger a PUT signal (overbought, high IV, above upper BB)."""
    base = dict(
        symbol="PUTSTOCK",
        rsi=78.0,            # > 70  -> +2
        iv_rank=65.0,        # > 50  -> +1
        bb_pband=1.1,        # > 1   -> +2
        atr_percentile=85.0, # > 80  -> +1
    )
    base.update(extra)
    return _make_screened_stock(**base)


def _make_call_stock(**extra) -> ScreenedStock:
    """Stock that should trigger a CALL signal (oversold, high IV, below lower BB)."""
    base = dict(
        symbol="CALLSTOCK",
        rsi=22.0,            # < 30  -> +2
        iv_rank=70.0,        # > 60  -> +1
        bb_pband=-0.1,       # < 0   -> +2
    )
    base.update(extra)
    return _make_screened_stock(**base)


def _make_hedge_stock(**extra) -> ScreenedStock:
    """Stock that should trigger a HEDGE signal."""
    base = dict(
        symbol="HEDGESTOCK",
        volatility_regime="extreme",  # high/extreme -> +2
        iv_rank=90.0,                 # > 80         -> +2
        hv_rank=85.0,                 # > 80         -> +1
        rsi=50.0,                     # neutral RSI so PUT check is skipped
        bb_pband=0.5,                 # neutral BB so PUT/CALL checks skipped
    )
    base.update(extra)
    return _make_screened_stock(**base)


def _make_volatility_stock(**extra) -> ScreenedStock:
    """Stock that should trigger a VOLATILITY_PLAY signal."""
    base = dict(
        symbol="VOLSTOCK",
        atr_percentile=95.0,  # > 90 -> +2
        iv_rank=20.0,         # < 30 -> +2
        bb_width=12.0,        # > 10 -> +1
        rsi=50.0,             # neutral
        bb_pband=0.5,         # neutral
    )
    base.update(extra)
    return _make_screened_stock(**base)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestSignalGeneratorInit:
    """Test that SignalGenerator initialises with a config."""

    def test_uses_provided_config(self):
        config = Settings(rsi_overbought=75.0)
        gen = SignalGenerator(config)
        assert gen.config.rsi_overbought == 75.0

    def test_uses_default_config_when_none(self):
        gen = SignalGenerator()
        assert gen.config is not None


class TestCalculateStrength:
    """Test _calculate_strength mapping."""

    def test_weak(self):
        gen = SignalGenerator(Settings())
        assert gen._calculate_strength(2) == SignalStrength.WEAK

    def test_moderate(self):
        gen = SignalGenerator(Settings())
        assert gen._calculate_strength(3) == SignalStrength.MODERATE

    def test_strong(self):
        gen = SignalGenerator(Settings())
        assert gen._calculate_strength(4) == SignalStrength.STRONG

    def test_very_strong(self):
        gen = SignalGenerator(Settings())
        assert gen._calculate_strength(5) == SignalStrength.VERY_STRONG
        assert gen._calculate_strength(6) == SignalStrength.VERY_STRONG

    def test_extreme(self):
        gen = SignalGenerator(Settings())
        assert gen._calculate_strength(7) == SignalStrength.EXTREME
        assert gen._calculate_strength(10) == SignalStrength.EXTREME


class TestPutSignalGeneration:
    """Test that a PUT signal is generated for overbought stocks."""

    def test_put_signal_generated(self):
        gen = SignalGenerator(Settings())
        stock = _make_put_stock()
        signals = gen.generate_signals([stock])

        assert len(signals) == 1
        sig = signals[0]
        assert sig.signal_type == SignalType.PUT_OPPORTUNITY
        assert sig.symbol == "PUTSTOCK"

    def test_put_signal_has_stop_loss_above_price(self):
        gen = SignalGenerator(Settings())
        stock = _make_put_stock()
        signals = gen.generate_signals([stock])

        sig = signals[0]
        assert sig.stop_loss > sig.current_price

    def test_put_signal_has_strike_below_price(self):
        gen = SignalGenerator(Settings())
        stock = _make_put_stock()
        signals = gen.generate_signals([stock])

        sig = signals[0]
        assert sig.suggested_strike < sig.current_price

    def test_put_not_generated_when_rsi_neutral(self):
        gen = SignalGenerator(Settings())
        stock = _make_screened_stock(rsi=50.0, iv_rank=55.0, bb_pband=0.5)
        signals = gen.generate_signals([stock])
        # Neutral stock should not produce any signal
        assert len(signals) == 0


class TestCallSignalGeneration:
    """Test that a CALL signal is generated for oversold stocks."""

    def test_call_signal_generated(self):
        gen = SignalGenerator(Settings())
        stock = _make_call_stock()
        signals = gen.generate_signals([stock])

        assert len(signals) == 1
        sig = signals[0]
        assert sig.signal_type == SignalType.CALL_OPPORTUNITY
        assert sig.symbol == "CALLSTOCK"

    def test_call_signal_has_stop_loss_below_price(self):
        gen = SignalGenerator(Settings())
        stock = _make_call_stock()
        signals = gen.generate_signals([stock])

        sig = signals[0]
        assert sig.stop_loss < sig.current_price

    def test_call_signal_has_strike_above_price(self):
        gen = SignalGenerator(Settings())
        stock = _make_call_stock()
        signals = gen.generate_signals([stock])

        sig = signals[0]
        assert sig.suggested_strike > sig.current_price


class TestHedgeSignalGeneration:
    """Test that a HEDGE signal is generated for high-vol stocks."""

    def test_hedge_signal_generated(self):
        gen = SignalGenerator(Settings())
        stock = _make_hedge_stock()
        signals = gen.generate_signals([stock])

        assert len(signals) == 1
        sig = signals[0]
        assert sig.signal_type == SignalType.HEDGE_SIGNAL
        assert sig.symbol == "HEDGESTOCK"

    def test_hedge_signal_strike_deep_otm(self):
        gen = SignalGenerator(Settings())
        stock = _make_hedge_stock()
        signals = gen.generate_signals([stock])

        sig = signals[0]
        # Hedge strike is 90% of current price
        assert sig.suggested_strike == pytest.approx(stock.current_price * 0.90, rel=0.01)


class TestVolatilityPlayGeneration:
    """Test that a VOLATILITY_PLAY signal is generated."""

    def test_volatility_signal_generated(self):
        gen = SignalGenerator(Settings())
        stock = _make_volatility_stock()
        signals = gen.generate_signals([stock])

        assert len(signals) == 1
        sig = signals[0]
        assert sig.signal_type == SignalType.VOLATILITY_PLAY
        assert sig.symbol == "VOLSTOCK"

    def test_volatility_signal_strike_atm(self):
        gen = SignalGenerator(Settings())
        stock = _make_volatility_stock()
        signals = gen.generate_signals([stock])

        sig = signals[0]
        assert sig.suggested_strike == stock.current_price


class TestGenerateSignalsSorting:
    """Test that signals are sorted by strength descending."""

    def test_sorted_by_strength(self):
        gen = SignalGenerator(Settings())
        # PUT stock meets 6 conditions (VERY_STRONG), CALL meets 5 (VERY_STRONG)
        put_stock = _make_put_stock()
        call_stock = _make_call_stock()
        signals = gen.generate_signals([put_stock, call_stock])

        assert len(signals) == 2
        # Both should be present; strongest first
        assert signals[0].strength.value >= signals[1].strength.value

    def test_max_signals_respected(self):
        gen = SignalGenerator(Settings())
        stocks = [_make_put_stock(symbol=f"S{i}") for i in range(5)]
        signals = gen.generate_signals(stocks, max_signals=2)
        assert len(signals) <= 2


class TestEmptyInput:
    """Test behaviour with empty or no-signal input."""

    def test_empty_list_returns_no_signals(self):
        gen = SignalGenerator(Settings())
        signals = gen.generate_signals([])
        assert signals == []

    def test_neutral_stock_returns_no_signals(self):
        gen = SignalGenerator(Settings())
        stock = _make_screened_stock()  # all neutral defaults
        signals = gen.generate_signals([stock])
        assert signals == []


class TestTradingSignalToDict:
    """Test the TradingSignal.to_dict serialisation."""

    def test_to_dict_has_required_keys(self):
        gen = SignalGenerator(Settings())
        stock = _make_put_stock()
        signals = gen.generate_signals([stock])

        d = signals[0].to_dict()
        expected_keys = {
            "symbol",
            "signal_type",
            "strength",
            "strength_name",
            "timestamp",
            "current_price",
            "suggested_strike",
            "entry_price",
            "stop_loss",
            "target_price",
            "rationale",
            "key_metrics",
            "risk_reward_ratio",
            "suggested_expiry_days",
            "suggested_delta",
            "scoring_breakdown",
        }
        assert expected_keys.issubset(d.keys())

    def test_to_dict_signal_type_is_string(self):
        gen = SignalGenerator(Settings())
        stock = _make_put_stock()
        signals = gen.generate_signals([stock])

        d = signals[0].to_dict()
        assert isinstance(d["signal_type"], str)
        assert d["signal_type"] == "PUT"
