"""Configuration settings for the NASDAQ Volatility Scanner."""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv


@dataclass
class Settings:
    """Application settings loaded from environment variables."""

    # Alpaca API
    alpaca_api_key: str = ""
    alpaca_secret_key: str = ""
    alpaca_base_url: str = "https://paper-api.alpaca.markets"

    # Webhook URLs
    discord_webhook_url: Optional[str] = None
    slack_webhook_url: Optional[str] = None

    # Screening thresholds
    iv_rank_threshold: float = 50.0
    rsi_overbought: float = 70.0
    rsi_oversold: float = 30.0
    atr_percentile_min: float = 70.0
    min_market_cap: float = 1_000_000_000  # $1B
    min_avg_volume: int = 1_000_000

    # Technical indicator periods
    atr_period: int = 14
    rsi_period: int = 14
    bollinger_period: int = 20
    bollinger_std: float = 2.0
    hv_period: int = 20

    # Scanner settings
    scan_interval_minutes: int = 60
    max_signals_per_scan: int = 10

    # NASDAQ-100 or custom watchlist
    watchlist: list = field(default_factory=list)

    @classmethod
    def load(cls, env_path: Optional[Path] = None) -> "Settings":
        """Load settings from environment variables."""
        if env_path:
            load_dotenv(env_path)
        else:
            load_dotenv()

        return cls(
            # Alpaca API
            alpaca_api_key=os.getenv("ALPACA_API_KEY", ""),
            alpaca_secret_key=os.getenv("ALPACA_SECRET_KEY", ""),
            alpaca_base_url=os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets"),

            # Webhooks
            discord_webhook_url=os.getenv("DISCORD_WEBHOOK_URL"),
            slack_webhook_url=os.getenv("SLACK_WEBHOOK_URL"),

            # Thresholds (with env overrides)
            iv_rank_threshold=float(os.getenv("IV_RANK_THRESHOLD", "50")),
            rsi_overbought=float(os.getenv("RSI_OVERBOUGHT", "70")),
            rsi_oversold=float(os.getenv("RSI_OVERSOLD", "30")),
            atr_percentile_min=float(os.getenv("ATR_PERCENTILE_MIN", "70")),
            min_market_cap=float(os.getenv("MIN_MARKET_CAP", "1000000000")),
            min_avg_volume=int(os.getenv("MIN_AVG_VOLUME", "1000000")),
        )

    def validate(self) -> list[str]:
        """Validate settings and return list of errors."""
        errors = []

        if not self.alpaca_api_key:
            errors.append("ALPACA_API_KEY is required")
        if not self.alpaca_secret_key:
            errors.append("ALPACA_SECRET_KEY is required")
        if not self.discord_webhook_url and not self.slack_webhook_url:
            errors.append("At least one webhook URL (Discord or Slack) is required")

        return errors

    @property
    def is_paper_trading(self) -> bool:
        """Check if using paper trading mode."""
        return "paper" in self.alpaca_base_url.lower()


# Default settings instance
settings = Settings.load()


# NASDAQ-100 constituents (as of 2024)
NASDAQ_100 = [
    "AAPL", "ABNB", "ADBE", "ADI", "ADP", "ADSK", "AEP", "AMAT", "AMD", "AMGN",
    "AMZN", "ANSS", "ARM", "ASML", "AVGO", "AZN", "BIIB", "BKNG", "BKR", "CCEP",
    "CDNS", "CDW", "CEG", "CHTR", "CMCSA", "COST", "CPRT", "CRWD", "CSCO", "CSGP",
    "CSX", "CTAS", "CTSH", "DDOG", "DLTR", "DXCM", "EA", "EXC", "FANG", "FAST",
    "FTNT", "GEHC", "GFS", "GILD", "GOOG", "GOOGL", "HON", "IDXX", "ILMN", "INTC",
    "INTU", "ISRG", "KDP", "KHC", "KLAC", "LRCX", "LULU", "MAR", "MCHP", "MDB",
    "MDLZ", "MELI", "META", "MNST", "MRNA", "MRVL", "MSFT", "MU", "NFLX", "NVDA",
    "NXPI", "ODFL", "ON", "ORLY", "PANW", "PAYX", "PCAR", "PDD", "PEP", "PYPL",
    "QCOM", "REGN", "ROP", "ROST", "SBUX", "SMCI", "SNPS", "SPLK", "TEAM", "TMUS",
    "TSLA", "TTD", "TTWO", "TXN", "VRSK", "VRTX", "WBD", "WDAY", "XEL", "ZS"
]
