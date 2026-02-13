"""Technical indicators: ATR, Bollinger Bands, RSI."""

import numpy as np
import pandas as pd
import ta


class TechnicalIndicators:
    """Calculate technical indicators for volatility analysis."""

    @staticmethod
    def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
        """
        Calculate Average True Range (ATR).

        ATR measures volatility by looking at the range of price movement.

        Args:
            df: DataFrame with high, low, close columns
            period: ATR period (default: 14)

        Returns:
            Series with ATR values
        """
        indicator = ta.volatility.AverageTrueRange(
            high=df["high"],
            low=df["low"],
            close=df["close"],
            window=period,
        )
        return indicator.average_true_range()

    @staticmethod
    def calculate_atr_percent(df: pd.DataFrame, period: int = 14) -> pd.Series:
        """
        Calculate ATR as percentage of price.

        Useful for comparing volatility across stocks with different prices.

        Args:
            df: DataFrame with high, low, close columns
            period: ATR period

        Returns:
            Series with ATR percentage values
        """
        atr = TechnicalIndicators.calculate_atr(df, period)
        return (atr / df["close"]) * 100

    @staticmethod
    def calculate_bollinger_bands(
        df: pd.DataFrame,
        period: int = 20,
        std_dev: float = 2.0,
    ) -> tuple[pd.Series, pd.Series, pd.Series]:
        """
        Calculate Bollinger Bands.

        Bollinger Bands measure volatility using standard deviations from a moving average.

        Args:
            df: DataFrame with close column
            period: Moving average period (default: 20)
            std_dev: Number of standard deviations (default: 2)

        Returns:
            Tuple of (upper band, middle band, lower band) Series
        """
        indicator = ta.volatility.BollingerBands(
            close=df["close"],
            window=period,
            window_dev=std_dev,
        )
        return (
            indicator.bollinger_hband(),
            indicator.bollinger_mavg(),
            indicator.bollinger_lband(),
        )

    @staticmethod
    def calculate_bollinger_width(df: pd.DataFrame, period: int = 20, std_dev: float = 2.0) -> pd.Series:
        """
        Calculate Bollinger Band Width.

        Width = (Upper - Lower) / Middle * 100
        Higher values indicate higher volatility.

        Args:
            df: DataFrame with close column
            period: Moving average period
            std_dev: Number of standard deviations

        Returns:
            Series with bandwidth percentage values
        """
        indicator = ta.volatility.BollingerBands(
            close=df["close"],
            window=period,
            window_dev=std_dev,
        )
        return indicator.bollinger_wband() * 100

    @staticmethod
    def calculate_bollinger_pband(df: pd.DataFrame, period: int = 20, std_dev: float = 2.0) -> pd.Series:
        """
        Calculate Bollinger %B.

        %B = (Price - Lower Band) / (Upper Band - Lower Band)
        Values > 1 indicate price above upper band, < 0 below lower band.

        Args:
            df: DataFrame with close column
            period: Moving average period
            std_dev: Number of standard deviations

        Returns:
            Series with %B values
        """
        indicator = ta.volatility.BollingerBands(
            close=df["close"],
            window=period,
            window_dev=std_dev,
        )
        return indicator.bollinger_pband()

    @staticmethod
    def calculate_rsi(df: pd.DataFrame, period: int = 14) -> pd.Series:
        """
        Calculate Relative Strength Index (RSI).

        RSI measures momentum on a 0-100 scale.
        > 70 = overbought, < 30 = oversold

        Args:
            df: DataFrame with close column
            period: RSI period (default: 14)

        Returns:
            Series with RSI values
        """
        indicator = ta.momentum.RSIIndicator(
            close=df["close"],
            window=period,
        )
        return indicator.rsi()

    @staticmethod
    def calculate_all(
        df: pd.DataFrame,
        atr_period: int = 14,
        rsi_period: int = 14,
        bb_period: int = 20,
        bb_std: float = 2.0,
    ) -> dict:
        """
        Calculate all technical indicators.

        Args:
            df: DataFrame with OHLCV data
            atr_period: ATR period
            rsi_period: RSI period
            bb_period: Bollinger Bands period
            bb_std: Bollinger Bands standard deviation

        Returns:
            Dictionary with all indicator values (latest)
        """
        if df.empty or len(df) < max(atr_period, rsi_period, bb_period):
            return {}

        atr = TechnicalIndicators.calculate_atr(df, atr_period)
        atr_pct = TechnicalIndicators.calculate_atr_percent(df, atr_period)
        rsi = TechnicalIndicators.calculate_rsi(df, rsi_period)
        bb_upper, bb_middle, bb_lower = TechnicalIndicators.calculate_bollinger_bands(df, bb_period, bb_std)
        bb_width = TechnicalIndicators.calculate_bollinger_width(df, bb_period, bb_std)
        bb_pband = TechnicalIndicators.calculate_bollinger_pband(df, bb_period, bb_std)

        # Calculate ATR percentile (how current ATR compares to historical)
        atr_values = atr.dropna()
        current_atr = atr_values.iloc[-1] if len(atr_values) > 0 else 0
        atr_percentile = (atr_values < current_atr).sum() / len(atr_values) * 100 if len(atr_values) > 0 else 50

        return {
            "atr": current_atr,
            "atr_percent": atr_pct.iloc[-1] if len(atr_pct) > 0 else 0,
            "atr_percentile": atr_percentile,
            "rsi": rsi.iloc[-1] if len(rsi) > 0 else 50,
            "bb_upper": bb_upper.iloc[-1] if len(bb_upper) > 0 else 0,
            "bb_middle": bb_middle.iloc[-1] if len(bb_middle) > 0 else 0,
            "bb_lower": bb_lower.iloc[-1] if len(bb_lower) > 0 else 0,
            "bb_width": bb_width.iloc[-1] if len(bb_width) > 0 else 0,
            "bb_pband": bb_pband.iloc[-1] if len(bb_pband) > 0 else 0.5,
            "price_vs_bb": (
                "above_upper" if bb_pband.iloc[-1] > 1
                else "below_lower" if bb_pband.iloc[-1] < 0
                else "within_bands"
            ) if len(bb_pband) > 0 else "unknown",
        }
