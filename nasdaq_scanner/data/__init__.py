"""Data fetching module."""
from .market_data import MarketDataFetcher
from .options_data import OptionsDataFetcher

try:
    from .alpaca_client import AlpacaClient
except ImportError:
    AlpacaClient = None
