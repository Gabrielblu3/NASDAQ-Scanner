"""Tests for configuration settings."""


from nasdaq_scanner.config.settings import NASDAQ_100, Settings


class TestSettingsDefaults:
    """Test that Settings defaults are sane."""

    def test_default_iv_rank_threshold(self):
        s = Settings()
        assert s.iv_rank_threshold == 50.0

    def test_default_rsi_overbought(self):
        s = Settings()
        assert s.rsi_overbought == 70.0

    def test_default_rsi_oversold(self):
        s = Settings()
        assert s.rsi_oversold == 30.0

    def test_default_atr_percentile_min(self):
        s = Settings()
        assert s.atr_percentile_min == 70.0

    def test_default_min_market_cap(self):
        s = Settings()
        assert s.min_market_cap == 1_000_000_000

    def test_default_min_avg_volume(self):
        s = Settings()
        assert s.min_avg_volume == 1_000_000

    def test_default_atr_period(self):
        s = Settings()
        assert s.atr_period == 14

    def test_default_rsi_period(self):
        s = Settings()
        assert s.rsi_period == 14

    def test_default_bollinger_period(self):
        s = Settings()
        assert s.bollinger_period == 20

    def test_default_bollinger_std(self):
        s = Settings()
        assert s.bollinger_std == 2.0

    def test_default_hv_period(self):
        s = Settings()
        assert s.hv_period == 20

    def test_default_scan_interval(self):
        s = Settings()
        assert s.scan_interval_minutes == 60

    def test_default_max_signals(self):
        s = Settings()
        assert s.max_signals_per_scan == 10

    def test_default_alpaca_base_url(self):
        s = Settings()
        assert s.alpaca_base_url == "https://paper-api.alpaca.markets"


class TestSettingsValidation:
    """Test the validate() method."""

    def test_validate_all_missing(self):
        s = Settings()
        errors = s.validate()
        assert "ALPACA_API_KEY is required" in errors
        assert "ALPACA_SECRET_KEY is required" in errors
        assert any("webhook" in e.lower() for e in errors)

    def test_validate_keys_set_no_webhook(self):
        s = Settings(alpaca_api_key="key", alpaca_secret_key="secret")
        errors = s.validate()
        assert "ALPACA_API_KEY is required" not in errors
        assert "ALPACA_SECRET_KEY is required" not in errors
        assert len(errors) == 1  # only the webhook error

    def test_validate_all_set(self):
        s = Settings(
            alpaca_api_key="key",
            alpaca_secret_key="secret",
            discord_webhook_url="https://discord.com/api/webhooks/123",
        )
        errors = s.validate()
        assert errors == []

    def test_validate_slack_webhook_also_works(self):
        s = Settings(
            alpaca_api_key="key",
            alpaca_secret_key="secret",
            slack_webhook_url="https://hooks.slack.com/services/xxx",
        )
        errors = s.validate()
        assert errors == []


class TestSettingsIsPaperTrading:
    """Test the is_paper_trading property."""

    def test_paper_url_is_paper(self):
        s = Settings(alpaca_base_url="https://paper-api.alpaca.markets")
        assert s.is_paper_trading is True

    def test_live_url_is_not_paper(self):
        s = Settings(alpaca_base_url="https://api.alpaca.markets")
        assert s.is_paper_trading is False


class TestNasdaq100List:
    """Test the NASDAQ_100 constant."""

    def test_nasdaq_100_has_100_symbols(self):
        assert len(NASDAQ_100) == 100

    def test_nasdaq_100_contains_major_stocks(self):
        major = ["AAPL", "MSFT", "AMZN", "GOOGL", "META", "NVDA", "TSLA"]
        for symbol in major:
            assert symbol in NASDAQ_100, f"{symbol} missing from NASDAQ_100"

    def test_nasdaq_100_all_uppercase_strings(self):
        for symbol in NASDAQ_100:
            assert isinstance(symbol, str)
            assert symbol == symbol.upper()

    def test_nasdaq_100_no_duplicates(self):
        assert len(NASDAQ_100) == len(set(NASDAQ_100))
