"""Stock screener for high volatility candidates."""

import logging
from dataclasses import dataclass
from typing import Optional

import pandas as pd

from nasdaq_scanner.config.settings import Settings, settings
from nasdaq_scanner.data.market_data import MarketDataFetcher
from nasdaq_scanner.data.options_data import OptionsDataFetcher
from nasdaq_scanner.indicators.technical import TechnicalIndicators
from nasdaq_scanner.indicators.volatility import VolatilityIndicators

logger = logging.getLogger(__name__)


@dataclass
class ScreenedStock:
    """Container for screened stock data."""

    symbol: str
    current_price: float
    change_pct: float

    # Technical indicators
    rsi: float
    atr_percent: float
    atr_percentile: float
    bb_width: float
    bb_pband: float

    # Volatility metrics
    historical_volatility: float
    hv_rank: float
    volatility_regime: str

    # Options metrics
    implied_volatility: Optional[float]
    iv_rank: Optional[float]
    iv_percentile: Optional[float]
    put_call_ratio: Optional[float]

    # Metadata
    market_cap: float
    avg_volume: int
    volume_ratio: float

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "symbol": self.symbol,
            "current_price": self.current_price,
            "change_pct": self.change_pct,
            "rsi": self.rsi,
            "atr_percent": self.atr_percent,
            "atr_percentile": self.atr_percentile,
            "bb_width": self.bb_width,
            "bb_pband": self.bb_pband,
            "historical_volatility": self.historical_volatility,
            "hv_rank": self.hv_rank,
            "volatility_regime": self.volatility_regime,
            "implied_volatility": self.implied_volatility,
            "iv_rank": self.iv_rank,
            "iv_percentile": self.iv_percentile,
            "put_call_ratio": self.put_call_ratio,
            "market_cap": self.market_cap,
            "avg_volume": self.avg_volume,
            "volume_ratio": self.volume_ratio,
        }


class StockScreener:
    """Screen stocks for high volatility trading opportunities."""

    def __init__(self, config: Optional[Settings] = None, use_yfinance_only: bool = False):
        """Initialize screener with configuration."""
        self.config = config or settings
        self.market_data = MarketDataFetcher(self.config, use_yfinance_only=use_yfinance_only)
        self.options_data = OptionsDataFetcher()

    def screen_stocks(
        self,
        symbols: Optional[list[str]] = None,
        include_options_data: bool = True,
    ) -> list[ScreenedStock]:
        """
        Screen stocks and calculate all indicators.

        Args:
            symbols: List of symbols to screen (default: watchlist)
            include_options_data: Whether to fetch options data (slower)

        Returns:
            List of ScreenedStock objects that pass filters
        """
        if symbols is None:
            symbols = self.market_data.get_watchlist()

        logger.info(f"Screening {len(symbols)} stocks...")

        # Fetch historical data for all symbols
        historical_data = self.market_data.fetch_historical_data(symbols)

        # Fetch VIX for correlation
        vix_data = self.market_data.get_vix_data()

        screened = []
        for symbol in symbols:
            if symbol not in historical_data:
                logger.debug(f"No data for {symbol}, skipping")
                continue

            df = historical_data[symbol]
            if len(df) < 14:
                logger.debug(f"Insufficient data for {symbol} ({len(df)} bars), skipping")
                continue

            try:
                stock = self._analyze_stock(symbol, df, vix_data, include_options_data)
                if stock and self._passes_filters(stock):
                    screened.append(stock)
            except Exception as e:
                logger.warning(f"Error analyzing {symbol}: {e}")
                continue

        # Sort by volatility score (combination of ATR percentile and IV rank)
        screened.sort(
            key=lambda s: (s.atr_percentile + (s.iv_rank or 50)) / 2,
            reverse=True,
        )

        logger.info(f"Found {len(screened)} stocks passing filters")
        return screened

    def _analyze_stock(
        self,
        symbol: str,
        df: pd.DataFrame,
        vix_data: pd.DataFrame,
        include_options: bool,
    ) -> Optional[ScreenedStock]:
        """Analyze a single stock and return ScreenedStock."""
        # Basic metrics
        basic = self.market_data.calculate_basic_metrics(df)
        if not basic:
            return None

        # Stock info (market cap, avg volume)
        info = self.market_data.get_stock_info(symbol)

        # Technical indicators
        tech = TechnicalIndicators.calculate_all(
            df,
            atr_period=self.config.atr_period,
            rsi_period=self.config.rsi_period,
            bb_period=self.config.bollinger_period,
            bb_std=self.config.bollinger_std,
        )

        # Volatility indicators
        vol = VolatilityIndicators.calculate_all(
            df,
            vix_df=vix_data,
            hv_period=self.config.hv_period,
        )

        # Options data (if enabled)
        options = {}
        if include_options:
            options = self.options_data.get_options_summary(symbol)

        return ScreenedStock(
            symbol=symbol,
            current_price=basic.get("current_price", 0),
            change_pct=basic.get("change_pct", 0),
            rsi=tech.get("rsi", 50),
            atr_percent=tech.get("atr_percent", 0),
            atr_percentile=tech.get("atr_percentile", 50),
            bb_width=tech.get("bb_width", 0),
            bb_pband=tech.get("bb_pband", 0.5),
            historical_volatility=vol.get("historical_volatility", 0),
            hv_rank=vol.get("hv_rank", 50),
            volatility_regime=vol.get("volatility_regime", "normal"),
            implied_volatility=options.get("implied_volatility"),
            iv_rank=options.get("iv_rank"),
            iv_percentile=options.get("iv_percentile"),
            put_call_ratio=options.get("put_call_ratio"),
            market_cap=info.get("market_cap", 0),
            avg_volume=info.get("avg_volume", 0),
            volume_ratio=basic.get("volume_ratio", 1),
        )

    def _passes_filters(self, stock: ScreenedStock) -> bool:
        """Check if stock passes screening filters."""
        # Market cap filter (skip if data unavailable - assume large cap NASDAQ stocks pass)
        if stock.market_cap > 0 and stock.market_cap < self.config.min_market_cap:
            return False

        # Volume filter (skip if data unavailable)
        if stock.avg_volume > 0 and stock.avg_volume < self.config.min_avg_volume:
            return False

        # ATR percentile filter (high volatility) - main filter
        if stock.atr_percentile is not None and stock.atr_percentile < self.config.atr_percentile_min:
            return False

        # IV Rank filter (if available)
        if stock.iv_rank is not None and stock.iv_rank < self.config.iv_rank_threshold:
            return False

        return True

    def get_overbought_stocks(self, screened: list[ScreenedStock]) -> list[ScreenedStock]:
        """Filter for overbought stocks (RSI > threshold)."""
        return [s for s in screened if s.rsi > self.config.rsi_overbought]

    def get_oversold_stocks(self, screened: list[ScreenedStock]) -> list[ScreenedStock]:
        """Filter for oversold stocks (RSI < threshold)."""
        return [s for s in screened if s.rsi < self.config.rsi_oversold]

    def get_high_iv_stocks(self, screened: list[ScreenedStock]) -> list[ScreenedStock]:
        """Filter for stocks with elevated IV."""
        return [
            s for s in screened
            if s.iv_rank is not None and s.iv_rank > 70
        ]

    def get_volatility_expansion(self, screened: list[ScreenedStock]) -> list[ScreenedStock]:
        """Filter for stocks with expanding volatility."""
        return [
            s for s in screened
            if s.volatility_regime in ("high", "extreme")
        ]
