"""Volatility indicators: Historical Volatility, VIX correlation."""

import numpy as np
import pandas as pd


class VolatilityIndicators:
    """Calculate volatility-based indicators."""

    @staticmethod
    def calculate_historical_volatility(
        df: pd.DataFrame,
        period: int = 20,
        annualize: bool = True,
    ) -> float:
        """
        Calculate Historical Volatility (HV).

        HV is the standard deviation of log returns, optionally annualized.

        Args:
            df: DataFrame with close column
            period: Lookback period (default: 20 trading days)
            annualize: Whether to annualize (default: True)

        Returns:
            Historical volatility as decimal (e.g., 0.35 = 35%)
        """
        if len(df) < period + 1:
            return 0.0

        # Calculate log returns
        log_returns = np.log(df["close"] / df["close"].shift(1))

        # Standard deviation of returns over period
        hv = log_returns.tail(period).std()

        # Annualize (252 trading days)
        if annualize:
            hv = hv * np.sqrt(252)

        return hv

    @staticmethod
    def calculate_hv_rank(df: pd.DataFrame, period: int = 20, lookback: int = 252) -> float:
        """
        Calculate Historical Volatility Rank.

        Shows where current HV sits relative to its range over the lookback period.

        Args:
            df: DataFrame with close column
            period: HV calculation period
            lookback: Lookback period for ranking (default: 1 year)

        Returns:
            HV Rank as percentage (0-100)
        """
        if len(df) < lookback:
            lookback = len(df)

        if lookback < period * 2:
            return 50.0

        # Calculate rolling HV
        log_returns = np.log(df["close"] / df["close"].shift(1))
        rolling_hv = log_returns.rolling(period).std() * np.sqrt(252)
        rolling_hv = rolling_hv.dropna()

        if len(rolling_hv) < 2:
            return 50.0

        current_hv = rolling_hv.iloc[-1]
        hv_min = rolling_hv.tail(lookback).min()
        hv_max = rolling_hv.tail(lookback).max()

        if hv_max == hv_min:
            return 50.0

        hv_rank = ((current_hv - hv_min) / (hv_max - hv_min)) * 100
        return max(0, min(100, hv_rank))

    @staticmethod
    def calculate_vix_correlation(
        stock_df: pd.DataFrame,
        vix_df: pd.DataFrame,
        period: int = 20,
    ) -> float:
        """
        Calculate correlation between stock returns and VIX changes.

        High positive correlation means stock moves with VIX (defensive).
        High negative correlation means stock moves opposite to VIX (typical).

        Args:
            stock_df: DataFrame with stock close prices
            vix_df: DataFrame with VIX close prices
            period: Correlation period (default: 20 days)

        Returns:
            Correlation coefficient (-1 to 1)
        """
        if len(stock_df) < period or len(vix_df) < period:
            return 0.0

        # Align dates
        stock_returns = stock_df["close"].pct_change().dropna()
        vix_returns = vix_df["close"].pct_change().dropna()

        # Get common dates
        common_idx = stock_returns.index.intersection(vix_returns.index)

        if len(common_idx) < period:
            return 0.0

        stock_aligned = stock_returns.loc[common_idx].tail(period)
        vix_aligned = vix_returns.loc[common_idx].tail(period)

        if len(stock_aligned) < 5 or len(vix_aligned) < 5:
            return 0.0

        correlation = stock_aligned.corr(vix_aligned)
        return correlation if not np.isnan(correlation) else 0.0

    @staticmethod
    def calculate_volatility_regime(df: pd.DataFrame) -> str:
        """
        Determine the current volatility regime.

        Args:
            df: DataFrame with close column

        Returns:
            Regime: "low", "normal", "high", or "extreme"
        """
        if len(df) < 60:
            return "unknown"

        hv_20 = VolatilityIndicators.calculate_historical_volatility(df, 20)
        hv_60 = VolatilityIndicators.calculate_historical_volatility(df, 60)

        # Annualized volatility thresholds
        if hv_20 < 0.15:
            return "low"
        elif hv_20 < 0.30:
            return "normal"
        elif hv_20 < 0.50:
            return "high"
        else:
            return "extreme"

    @staticmethod
    def calculate_volatility_trend(df: pd.DataFrame) -> str:
        """
        Determine if volatility is increasing or decreasing.

        Args:
            df: DataFrame with close column

        Returns:
            Trend: "increasing", "decreasing", or "stable"
        """
        if len(df) < 30:
            return "unknown"

        # Compare short-term vs long-term HV
        hv_10 = VolatilityIndicators.calculate_historical_volatility(df, 10)
        hv_20 = VolatilityIndicators.calculate_historical_volatility(df, 20)

        ratio = hv_10 / hv_20 if hv_20 > 0 else 1

        if ratio > 1.2:
            return "increasing"
        elif ratio < 0.8:
            return "decreasing"
        else:
            return "stable"

    @staticmethod
    def calculate_all(
        df: pd.DataFrame,
        vix_df: pd.DataFrame = None,
        hv_period: int = 20,
    ) -> dict:
        """
        Calculate all volatility indicators.

        Args:
            df: DataFrame with OHLCV data
            vix_df: DataFrame with VIX data (optional)
            hv_period: Historical volatility period

        Returns:
            Dictionary with all indicator values
        """
        hv = VolatilityIndicators.calculate_historical_volatility(df, hv_period)
        hv_rank = VolatilityIndicators.calculate_hv_rank(df, hv_period)
        regime = VolatilityIndicators.calculate_volatility_regime(df)
        trend = VolatilityIndicators.calculate_volatility_trend(df)

        result = {
            "historical_volatility": hv,
            "hv_annualized_pct": hv * 100,
            "hv_rank": hv_rank,
            "volatility_regime": regime,
            "volatility_trend": trend,
        }

        if vix_df is not None and not vix_df.empty:
            vix_corr = VolatilityIndicators.calculate_vix_correlation(df, vix_df)
            result["vix_correlation"] = vix_corr
            result["vix_correlation_strength"] = (
                "strong_negative" if vix_corr < -0.5
                else "moderate_negative" if vix_corr < -0.2
                else "weak" if abs(vix_corr) < 0.2
                else "moderate_positive" if vix_corr < 0.5
                else "strong_positive"
            )

        return result
