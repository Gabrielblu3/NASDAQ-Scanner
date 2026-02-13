"""Market data fetching and processing."""

import logging
from datetime import datetime
from typing import Optional

import pandas as pd
import yfinance as yf

from nasdaq_scanner.config.settings import NASDAQ_100, Settings, settings

logger = logging.getLogger(__name__)


class MarketDataFetcher:
    """Fetches and processes market data from multiple sources."""

    def __init__(self, config: Optional[Settings] = None, use_yfinance_only: bool = False):
        """Initialize data fetcher.

        Args:
            config: Settings object
            use_yfinance_only: If True, skip Alpaca and use only yfinance
        """
        self.config = config or settings
        self.use_yfinance_only = use_yfinance_only
        self.alpaca = None

        if not use_yfinance_only and self.config.alpaca_api_key:
            try:
                from nasdaq_scanner.data.alpaca_client import AlpacaClient
                self.alpaca = AlpacaClient(self.config)
            except Exception as e:
                logger.warning(f"Could not initialize Alpaca client: {e}. Using yfinance only.")

    def get_watchlist(self) -> list[str]:
        """Get the watchlist of symbols to scan."""
        if self.config.watchlist:
            return self.config.watchlist
        return NASDAQ_100

    def fetch_historical_data(
        self,
        symbols: Optional[list[str]] = None,
        days: int = 100,
    ) -> dict[str, pd.DataFrame]:
        """
        Fetch historical OHLCV data for symbols.

        Args:
            symbols: List of symbols (default: watchlist)
            days: Number of days of history

        Returns:
            Dictionary mapping symbol to DataFrame
        """
        if symbols is None:
            symbols = self.get_watchlist()

        logger.info(f"Fetching historical data for {len(symbols)} symbols...")

        # Use Alpaca if available, otherwise yfinance
        if self.alpaca and not self.use_yfinance_only:
            return self.alpaca.get_bars(symbols, limit=days)
        else:
            return self._fetch_yfinance_data(symbols, days)

    def _fetch_yfinance_data(self, symbols: list[str], days: int) -> dict[str, pd.DataFrame]:
        """Fetch data using yfinance bulk download."""
        result = {}

        # Convert days to period string
        if days <= 5:
            period = "5d"
        elif days <= 30:
            period = "1mo"
        elif days <= 90:
            period = "3mo"
        elif days <= 180:
            period = "6mo"
        else:
            period = "1y"

        try:
            # Use bulk download - more reliable
            data = yf.download(
                symbols,
                period=period,
                group_by="ticker",
                auto_adjust=True,
                progress=False,
                threads=True,
            )

            if data.empty:
                logger.warning("No data returned from yfinance")
                return result

            # Handle single vs multiple symbols
            if len(symbols) == 1:
                symbol = symbols[0]
                df = data.rename(columns={
                    "Open": "open",
                    "High": "high",
                    "Low": "low",
                    "Close": "close",
                    "Volume": "volume"
                })
                if not df.empty:
                    result[symbol] = df[["open", "high", "low", "close", "volume"]]
            else:
                for symbol in symbols:
                    try:
                        if symbol in data.columns.get_level_values(0):
                            df = data[symbol].rename(columns={
                                "Open": "open",
                                "High": "high",
                                "Low": "low",
                                "Close": "close",
                                "Volume": "volume"
                            })
                            if not df.empty and not df["close"].isna().all():
                                result[symbol] = df[["open", "high", "low", "close", "volume"]].dropna()
                    except Exception as e:
                        logger.debug(f"Error processing {symbol}: {e}")

        except Exception as e:
            logger.warning(f"Error in bulk download: {e}")

        logger.info(f"Successfully fetched data for {len(result)} symbols")
        return result

    def fetch_latest_prices(
        self,
        symbols: Optional[list[str]] = None,
    ) -> dict[str, dict]:
        """
        Fetch latest quotes for symbols.

        Args:
            symbols: List of symbols (default: watchlist)

        Returns:
            Dictionary mapping symbol to quote data
        """
        if symbols is None:
            symbols = self.get_watchlist()

        if self.alpaca and not self.use_yfinance_only:
            return self.alpaca.get_latest_quotes(symbols)
        else:
            # Use yfinance for latest prices
            result = {}
            for symbol in symbols:
                try:
                    ticker = yf.Ticker(symbol)
                    info = ticker.info
                    price = info.get("currentPrice") or info.get("regularMarketPrice", 0)
                    result[symbol] = {
                        "bid_price": price,
                        "ask_price": price,
                        "mid_price": price,
                    }
                except Exception as e:
                    logger.warning(f"Error fetching quote for {symbol}: {e}")
            return result

    def get_stock_info(self, symbol: str) -> dict:
        """
        Get stock information using yfinance.

        Args:
            symbol: Stock symbol

        Returns:
            Dictionary with stock info (market cap, sector, etc.)
        """
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            return {
                "symbol": symbol,
                "name": info.get("longName", symbol),
                "market_cap": info.get("marketCap", 0),
                "sector": info.get("sector", "Unknown"),
                "industry": info.get("industry", "Unknown"),
                "beta": info.get("beta", 1.0),
                "avg_volume": info.get("averageVolume", 0),
                "fifty_two_week_high": info.get("fiftyTwoWeekHigh", 0),
                "fifty_two_week_low": info.get("fiftyTwoWeekLow", 0),
            }
        except Exception as e:
            logger.warning(f"Error fetching info for {symbol}: {e}")
            return {"symbol": symbol, "market_cap": 0, "avg_volume": 0}

    def get_vix_data(self, days: int = 100) -> pd.DataFrame:
        """
        Fetch VIX index data.

        Args:
            days: Number of days of history

        Returns:
            DataFrame with VIX data
        """
        try:
            vix = yf.Ticker("^VIX")
            hist = vix.history(period=f"{days}d")
            return hist[["Open", "High", "Low", "Close", "Volume"]].rename(
                columns={"Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"}
            )
        except Exception as e:
            logger.warning(f"Error fetching VIX data: {e}")
            return pd.DataFrame()

    def calculate_basic_metrics(self, df: pd.DataFrame) -> dict:
        """
        Calculate basic metrics from OHLCV data.

        Args:
            df: DataFrame with OHLCV data

        Returns:
            Dictionary with basic metrics
        """
        if df.empty or len(df) < 2:
            return {}

        latest = df.iloc[-1]
        prev = df.iloc[-2]

        return {
            "current_price": latest["close"],
            "prev_close": prev["close"],
            "change_pct": ((latest["close"] - prev["close"]) / prev["close"]) * 100,
            "day_range_pct": ((latest["high"] - latest["low"]) / latest["low"]) * 100,
            "volume": latest["volume"],
            "avg_volume_20d": df["volume"].tail(20).mean(),
            "volume_ratio": latest["volume"] / df["volume"].tail(20).mean() if df["volume"].tail(20).mean() > 0 else 0,
            "high_52w": df["high"].tail(252).max() if len(df) >= 252 else df["high"].max(),
            "low_52w": df["low"].tail(252).min() if len(df) >= 252 else df["low"].min(),
        }
