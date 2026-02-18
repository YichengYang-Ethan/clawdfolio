"""Tests for market utilities."""

from datetime import date, time

from clawdfolio.market.calendar import (
    is_trading_day,
    is_weekend,
    next_trading_day,
    prev_trading_day,
    trading_days_between,
)
from clawdfolio.market.hours import (
    MarketHours,
    MarketStatus,
    get_market_status,
)


class TestMarketHours:
    """Tests for market hours."""

    def test_us_market_hours(self):
        """Test US market hours configuration."""
        us = MarketHours.US
        assert us.market == "US"
        assert us.session.market_open == time(9, 30)
        assert us.session.market_close == time(16, 0)

    def test_hk_market_hours(self):
        """Test HK market hours configuration."""
        hk = MarketHours.HK
        assert hk.market == "HK"
        assert hk.session.market_open == time(9, 30)
        assert hk.session.market_close == time(16, 0)

    def test_market_status_enum(self):
        """Test MarketStatus enum values."""
        assert MarketStatus.PRE_MARKET == "pre_market"
        assert MarketStatus.OPEN == "open"
        assert MarketStatus.AFTER_HOURS == "after_hours"
        assert MarketStatus.CLOSED == "closed"

    def test_get_market_status_returns_valid_status(self):
        """Test that get_market_status returns a valid MarketStatus."""
        status = get_market_status("US")
        assert status in [
            MarketStatus.PRE_MARKET,
            MarketStatus.OPEN,
            MarketStatus.AFTER_HOURS,
            MarketStatus.CLOSED,
        ]


class TestTradingCalendar:
    """Tests for trading calendar."""

    def test_is_weekend_saturday(self):
        """Test Saturday is weekend."""
        saturday = date(2024, 1, 6)  # A Saturday
        assert is_weekend(saturday) is True

    def test_is_weekend_sunday(self):
        """Test Sunday is weekend."""
        sunday = date(2024, 1, 7)  # A Sunday
        assert is_weekend(sunday) is True

    def test_is_weekend_weekday(self):
        """Test weekday is not weekend."""
        monday = date(2024, 1, 8)  # A Monday
        assert is_weekend(monday) is False

    def test_is_trading_day_weekend(self):
        """Test weekend is not trading day."""
        saturday = date(2024, 1, 6)
        assert is_trading_day(saturday) is False

    def test_is_trading_day_weekday(self):
        """Test regular weekday is trading day."""
        # Pick a non-holiday weekday
        tuesday = date(2024, 1, 9)  # A Tuesday, not a holiday
        assert is_trading_day(tuesday) is True

    def test_is_trading_day_holiday(self):
        """Test US holiday is not trading day."""
        christmas = date(2024, 12, 25)
        assert is_trading_day(christmas, market="US") is False

    def test_next_trading_day_from_friday(self):
        """Test next trading day from Friday is Monday."""
        friday = date(2024, 1, 5)
        next_day = next_trading_day(friday)
        assert next_day == date(2024, 1, 8)  # Monday

    def test_prev_trading_day_from_monday(self):
        """Test previous trading day from Monday is Friday."""
        monday = date(2024, 1, 8)
        prev_day = prev_trading_day(monday)
        assert prev_day == date(2024, 1, 5)  # Friday

    def test_trading_days_between(self):
        """Test counting trading days between dates."""
        start = date(2024, 1, 8)  # Monday
        end = date(2024, 1, 12)  # Friday
        days = trading_days_between(start, end)

        # Should be 5 weekdays
        assert len(days) == 5
        assert days[0] == start
        assert days[-1] == end

    def test_trading_days_between_with_weekend(self):
        """Test trading days excludes weekend."""
        start = date(2024, 1, 5)  # Friday
        end = date(2024, 1, 8)  # Monday
        days = trading_days_between(start, end)

        # Should be 2: Friday and Monday
        assert len(days) == 2
        assert date(2024, 1, 6) not in days  # Saturday
        assert date(2024, 1, 7) not in days  # Sunday
