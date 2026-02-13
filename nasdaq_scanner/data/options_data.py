"""Options data fetching using yfinance."""

import logging
from datetime import datetime, timedelta
from typing import Optional

import numpy as np
import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)


class OptionsDataFetcher:
    """Fetches options data and calculates IV metrics."""

    def __init__(self):
        """Initialize options data fetcher."""
        self._iv_cache: dict[str, list[float]] = {}

    def get_options_chain(
        self,
        symbol: str,
        expiry_date: Optional[str] = None,
    ) -> tuple[pd.DataFrame, pd.DataFrame]:
        """
        Fetch options chain for a symbol.

        Args:
            symbol: Stock symbol
            expiry_date: Specific expiry date (default: nearest)

        Returns:
            Tuple of (calls DataFrame, puts DataFrame)
        """
        try:
            ticker = yf.Ticker(symbol)
            expirations = ticker.options

            if not expirations:
                logger.warning(f"No options available for {symbol}")
                return pd.DataFrame(), pd.DataFrame()

            # Use specified expiry or nearest one
            if expiry_date and expiry_date in expirations:
                exp = expiry_date
            else:
                exp = expirations[0]  # Nearest expiry

            chain = ticker.option_chain(exp)
            return chain.calls, chain.puts

        except Exception as e:
            logger.warning(f"Error fetching options for {symbol}: {e}")
            return pd.DataFrame(), pd.DataFrame()

    def get_implied_volatility(self, symbol: str) -> Optional[float]:
        """
        Get current implied volatility for ATM options.

        Args:
            symbol: Stock symbol

        Returns:
            Implied volatility as decimal (e.g., 0.35 = 35%)
        """
        try:
            ticker = yf.Ticker(symbol)
            current_price = ticker.info.get("currentPrice") or ticker.info.get("regularMarketPrice", 0)

            if not current_price:
                return None

            expirations = ticker.options
            if not expirations:
                return None

            # Get options expiring in 30-45 days for IV calculation
            target_date = datetime.now() + timedelta(days=30)
            best_exp = min(
                expirations,
                key=lambda x: abs((datetime.strptime(x, "%Y-%m-%d") - target_date).days)
            )

            chain = ticker.option_chain(best_exp)
            calls = chain.calls
            puts = chain.puts

            # Find ATM options
            calls["distance"] = abs(calls["strike"] - current_price)
            puts["distance"] = abs(puts["strike"] - current_price)

            atm_call = calls.loc[calls["distance"].idxmin()] if not calls.empty else None
            atm_put = puts.loc[puts["distance"].idxmin()] if not puts.empty else None

            # Average IV of ATM call and put
            ivs = []
            if atm_call is not None and "impliedVolatility" in calls.columns:
                iv = atm_call.get("impliedVolatility")
                if iv and not np.isnan(iv):
                    ivs.append(iv)
            if atm_put is not None and "impliedVolatility" in puts.columns:
                iv = atm_put.get("impliedVolatility")
                if iv and not np.isnan(iv):
                    ivs.append(iv)

            if ivs:
                avg_iv = np.mean(ivs)
                # Cache for IV rank calculation
                if symbol not in self._iv_cache:
                    self._iv_cache[symbol] = []
                self._iv_cache[symbol].append(avg_iv)
                # Keep last 252 values (1 year)
                self._iv_cache[symbol] = self._iv_cache[symbol][-252:]
                return avg_iv

            return None

        except Exception as e:
            logger.warning(f"Error calculating IV for {symbol}: {e}")
            return None

    def get_iv_rank(self, symbol: str, current_iv: Optional[float] = None) -> Optional[float]:
        """
        Calculate IV Rank (where current IV sits in 52-week range).

        IV Rank = (Current IV - 52w Low IV) / (52w High IV - 52w Low IV) * 100

        Args:
            symbol: Stock symbol
            current_iv: Current IV (fetched if not provided)

        Returns:
            IV Rank as percentage (0-100)
        """
        if current_iv is None:
            current_iv = self.get_implied_volatility(symbol)

        if current_iv is None:
            return None

        # Use cached IV history or fetch historical IV
        iv_history = self._iv_cache.get(symbol, [])

        if len(iv_history) < 20:
            # Not enough history, estimate from stock volatility
            iv_history = self._estimate_iv_history(symbol)

        if not iv_history:
            return None

        iv_low = min(iv_history)
        iv_high = max(iv_history)

        if iv_high == iv_low:
            return 50.0  # No range, return middle

        iv_rank = ((current_iv - iv_low) / (iv_high - iv_low)) * 100
        return max(0, min(100, iv_rank))

    def get_iv_percentile(self, symbol: str, current_iv: Optional[float] = None) -> Optional[float]:
        """
        Calculate IV Percentile (% of days IV was lower than current).

        Args:
            symbol: Stock symbol
            current_iv: Current IV (fetched if not provided)

        Returns:
            IV Percentile as percentage (0-100)
        """
        if current_iv is None:
            current_iv = self.get_implied_volatility(symbol)

        if current_iv is None:
            return None

        iv_history = self._iv_cache.get(symbol, [])

        if len(iv_history) < 20:
            iv_history = self._estimate_iv_history(symbol)

        if not iv_history:
            return None

        days_below = sum(1 for iv in iv_history if iv < current_iv)
        return (days_below / len(iv_history)) * 100

    def _estimate_iv_history(self, symbol: str) -> list[float]:
        """
        Estimate historical IV from historical volatility.

        This is an approximation used when real IV history isn't available.
        """
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="1y")

            if hist.empty:
                return []

            # Calculate rolling 20-day realized volatility as IV proxy
            returns = hist["Close"].pct_change()
            rolling_vol = returns.rolling(20).std() * np.sqrt(252)

            # IV is typically higher than realized vol, apply multiplier
            estimated_iv = (rolling_vol * 1.1).dropna().tolist()
            return estimated_iv

        except Exception as e:
            logger.warning(f"Error estimating IV history for {symbol}: {e}")
            return []

    def get_options_summary(self, symbol: str) -> dict:
        """
        Get comprehensive options summary for a symbol.

        Args:
            symbol: Stock symbol

        Returns:
            Dictionary with IV, IV Rank, IV Percentile, and basic chain info
        """
        iv = self.get_implied_volatility(symbol)
        iv_rank = self.get_iv_rank(symbol, iv) if iv else None
        iv_percentile = self.get_iv_percentile(symbol, iv) if iv else None

        calls, puts = self.get_options_chain(symbol)

        return {
            "implied_volatility": iv,
            "iv_rank": iv_rank,
            "iv_percentile": iv_percentile,
            "has_options": not calls.empty,
            "num_call_strikes": len(calls),
            "num_put_strikes": len(puts),
            "total_call_oi": calls["openInterest"].sum() if "openInterest" in calls.columns else 0,
            "total_put_oi": puts["openInterest"].sum() if "openInterest" in puts.columns else 0,
            "put_call_ratio": (
                puts["openInterest"].sum() / calls["openInterest"].sum()
                if "openInterest" in calls.columns and calls["openInterest"].sum() > 0
                else None
            ),
        }
