"""Tests for earnings calendar monitoring."""

from datetime import date, datetime, timedelta
from decimal import Decimal
from unittest.mock import patch

from clawdfolio.core.types import (
    AlertType,
    Exchange,
    Portfolio,
    Position,
    Symbol,
)
from clawdfolio.monitors.earnings import (
    EarningsEvent,
    EarningsMonitor,
    format_earnings_calendar,
    get_upcoming_earnings,
)


def _make_position(ticker, weight=0.10, market_value=10000):
    pos = Position(
        symbol=Symbol(ticker=ticker, exchange=Exchange.NYSE),
        quantity=Decimal("100"),
        market_value=Decimal(str(market_value)),
    )
    pos.weight = weight
    return pos


def _make_portfolio(positions, net_assets=100000):
    return Portfolio(
        positions=positions,
        net_assets=Decimal(str(net_assets)),
        market_value=Decimal(str(net_assets)),
    )


class TestEarningsMonitor:
    @patch("clawdfolio.monitors.earnings.get_earnings_date")
    def test_earnings_alert_within_window(self, mock_earnings):
        """Earnings within alert window should trigger alert."""
        earnings_date = datetime.now() + timedelta(days=3)
        mock_earnings.return_value = (earnings_date, "BMO")

        pos = _make_position("AAPL")
        portfolio = _make_portfolio([pos])
        monitor = EarningsMonitor(alert_days=7)
        alerts = monitor.check_portfolio(portfolio)
        assert len(alerts) == 1
        assert alerts[0].type == AlertType.EARNINGS
        assert "AAPL" in alerts[0].title

    @patch("clawdfolio.monitors.earnings.get_earnings_date")
    def test_earnings_outside_window(self, mock_earnings):
        """Earnings outside alert window should not trigger."""
        earnings_date = datetime.now() + timedelta(days=20)
        mock_earnings.return_value = (earnings_date, "AMC")

        pos = _make_position("AAPL")
        portfolio = _make_portfolio([pos])
        monitor = EarningsMonitor(alert_days=7)
        alerts = monitor.check_portfolio(portfolio)
        assert len(alerts) == 0

    @patch("clawdfolio.monitors.earnings.get_earnings_date")
    def test_earnings_today(self, mock_earnings):
        """Earnings today should show TODAY in title."""
        mock_earnings.return_value = (datetime.now(), "BMO")

        pos = _make_position("AAPL")
        portfolio = _make_portfolio([pos])
        monitor = EarningsMonitor(alert_days=7)
        alerts = monitor.check_portfolio(portfolio)
        assert len(alerts) == 1
        assert "TODAY" in alerts[0].title

    @patch("clawdfolio.monitors.earnings.get_earnings_date")
    def test_no_earnings_data(self, mock_earnings):
        """No earnings data should produce no alerts."""
        mock_earnings.return_value = None

        pos = _make_position("AAPL")
        portfolio = _make_portfolio([pos])
        monitor = EarningsMonitor()
        alerts = monitor.check_portfolio(portfolio)
        assert len(alerts) == 0


class TestGetUpcomingEarnings:
    @patch("clawdfolio.monitors.earnings.get_earnings_date")
    def test_upcoming_earnings(self, mock_earnings):
        """Should return events within days_ahead window."""
        earnings_dt = datetime.now() + timedelta(days=5)
        mock_earnings.return_value = (earnings_dt, "AMC")

        pos = _make_position("MSFT", weight=0.15)
        portfolio = _make_portfolio([pos])
        events = get_upcoming_earnings(portfolio, days_ahead=14)
        assert len(events) == 1
        assert events[0].ticker == "MSFT"
        assert events[0].timing == "AMC"
        assert events[0].days_until == 5

    @patch("clawdfolio.monitors.earnings.get_earnings_date")
    def test_sorted_by_date(self, mock_earnings):
        """Events should be sorted by date."""

        def side_effect(ticker):
            if ticker == "AAPL":
                return (datetime.now() + timedelta(days=7), "BMO")
            elif ticker == "MSFT":
                return (datetime.now() + timedelta(days=3), "AMC")
            return None

        mock_earnings.side_effect = side_effect
        positions = [_make_position("AAPL"), _make_position("MSFT")]
        portfolio = _make_portfolio(positions)
        events = get_upcoming_earnings(portfolio, days_ahead=14)
        assert len(events) == 2
        assert events[0].ticker == "MSFT"  # Earlier date first
        assert events[1].ticker == "AAPL"


class TestFormatEarningsCalendar:
    def test_empty_events(self):
        result = format_earnings_calendar([])
        assert "No upcoming earnings" in result

    def test_format_with_events(self):
        today = date.today()
        events = [
            EarningsEvent(
                ticker="AAPL",
                date=today,
                timing="BMO",
                days_until=0,
                weight=0.15,
            ),
            EarningsEvent(
                ticker="MSFT",
                date=today + timedelta(days=3),
                timing="AMC",
                days_until=3,
                weight=0.10,
            ),
        ]
        result = format_earnings_calendar(events)
        assert "AAPL" in result
        assert "MSFT" in result
        assert "TODAY" in result

    def test_tomorrow_label(self):
        tomorrow = date.today() + timedelta(days=1)
        events = [
            EarningsEvent(
                ticker="GOOG",
                date=tomorrow,
                timing="TBD",
                days_until=1,
                weight=0.05,
            ),
        ]
        result = format_earnings_calendar(events)
        assert "Tomorrow" in result
