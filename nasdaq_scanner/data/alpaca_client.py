"""Alpaca API client wrapper."""

import logging
from datetime import datetime, timedelta
from typing import Optional

import pandas as pd
from alpaca.data import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest, StockLatestQuoteRequest
from alpaca.data.timeframe import TimeFrame

from nasdaq_scanner.config.settings import Settings, settings

logger = logging.getLogger(__name__)


class AlpacaClient:
    """Wrapper for Alpaca Market Data API."""

    def __init__(self, config: Optional[Settings] = None):
        """Initialize Alpaca client with API credentials."""
        self.config = config or settings
        self.client = StockHistoricalDataClient(
            api_key=self.config.alpaca_api_key,
            secret_key=self.config.alpaca_secret_key,
        )

    def get_bars(
        self,
        symbols: list[str],
        timeframe: TimeFrame = TimeFrame.Day,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        limit: int = 100,
    ) -> dict[str, pd.DataFrame]:
        """
        Fetch historical bar data for multiple symbols.

        Args:
            symbols: List of stock symbols
            timeframe: Bar timeframe (Day, Hour, Minute)
            start: Start datetime (default: 100 days ago)
            end: End datetime (default: now)
            limit: Maximum bars per symbol

        Returns:
            Dictionary mapping symbol to DataFrame with OHLCV data
        """
        if start is None:
            start = datetime.now() - timedelta(days=limit + 50)
        if end is None:
            end = datetime.now()

        request = StockBarsRequest(
            symbol_or_symbols=symbols,
            timeframe=timeframe,
            start=start,
            end=end,
            limit=limit,
        )

        result = {}

        # Fetch symbols individually to avoid API limitations
        for symbol in symbols:
            try:
                single_request = StockBarsRequest(
                    symbol_or_symbols=symbol,
                    timeframe=timeframe,
                    start=start,
                    end=end,
                    limit=limit,
                )
                bars = self.client.get_stock_bars(single_request)

                if symbol in bars.data:
                    df = pd.DataFrame([
                        {
                            "timestamp": bar.timestamp,
                            "open": bar.open,
                            "high": bar.high,
                            "low": bar.low,
                            "close": bar.close,
                            "volume": bar.volume,
                            "vwap": bar.vwap,
                        }
                        for bar in bars.data[symbol]
                    ])
                    if not df.empty:
                        df.set_index("timestamp", inplace=True)
                        df.index = pd.to_datetime(df.index)
                        result[symbol] = df

            except Exception as e:
                logger.warning(f"Error fetching {symbol}: {e}")

        return result

    def get_latest_quotes(self, symbols: list[str]) -> dict[str, dict]:
        """
        Fetch latest quotes for multiple symbols.

        Args:
            symbols: List of stock symbols

        Returns:
            Dictionary mapping symbol to quote data
        """
        request = StockLatestQuoteRequest(symbol_or_symbols=symbols)

        try:
            quotes = self.client.get_stock_latest_quote(request)
            result = {}

            for symbol, quote in quotes.items():
                result[symbol] = {
                    "bid_price": quote.bid_price,
                    "ask_price": quote.ask_price,
                    "bid_size": quote.bid_size,
                    "ask_size": quote.ask_size,
                    "timestamp": quote.timestamp,
                    "mid_price": (quote.bid_price + quote.ask_price) / 2,
                }

            return result

        except Exception as e:
            logger.error(f"Error fetching quotes: {e}")
            return {}

    def get_vix_data(self, days: int = 100) -> pd.DataFrame:
        """
        Fetch VIX index data (using VIXY ETF as proxy).

        Args:
            days: Number of days of history

        Returns:
            DataFrame with VIX proxy data
        """
        bars = self.get_bars(["VIXY"], limit=days)
        return bars.get("VIXY", pd.DataFrame())
