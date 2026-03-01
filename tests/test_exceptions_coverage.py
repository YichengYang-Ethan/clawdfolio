"""Tests for exceptions module."""

from clawdfolio.core.exceptions import (
    AuthenticationError,
    BrokerError,
    ConfigError,
    MarketClosedError,
    MarketDataError,
    PortfolioMonitorError,
    RateLimitError,
)


class TestExceptions:
    """Tests for custom exceptions."""

    def test_portfolio_monitor_error(self):
        e = PortfolioMonitorError("test error")
        assert str(e) == "test error"

    def test_broker_error(self):
        e = BrokerError("longport", "connection failed")
        assert "longport" in str(e)
        assert e.broker == "longport"

    def test_config_error(self):
        e = ConfigError("bad config")
        assert "bad config" in str(e)

    def test_market_data_error(self):
        e = MarketDataError("AAPL", "yfinance", "timeout")
        assert e.ticker == "AAPL"
        assert e.source == "yfinance"

    def test_authentication_error(self):
        e = AuthenticationError("futu")
        assert "futu" in str(e)
        assert "Authentication" in str(e)

    def test_rate_limit_error(self):
        e = RateLimitError("longport", retry_after=60)
        assert e.retry_after == 60
        assert "60s" in str(e)

    def test_rate_limit_error_no_retry(self):
        e = RateLimitError("longport")
        assert "Rate limit" in str(e)

    def test_market_closed_error(self):
        e = MarketClosedError("HK")
        assert e.market == "HK"
        assert "closed" in str(e)

    def test_market_closed_error_default(self):
        e = MarketClosedError()
        assert e.market == "US"
