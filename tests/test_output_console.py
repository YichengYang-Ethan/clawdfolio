"""Tests for console output module."""

from datetime import datetime
from decimal import Decimal

from clawdfolio.core.types import (
    Alert,
    AlertSeverity,
    AlertType,
    Portfolio,
    Position,
    RiskMetrics,
    Symbol,
)
from clawdfolio.output.console import (
    RICH_AVAILABLE,
    ConsoleFormatter,
    _format_money,
    _format_pct,
    _get_color,
    print_portfolio,
    print_risk_metrics,
)
from clawdfolio.storage.models import PerformanceMetrics, PortfolioSnapshot
from clawdfolio.strategies.rebalance import RebalanceAction


def _make_portfolio():
    positions = [
        Position(
            symbol=Symbol(ticker="AAPL"),
            quantity=Decimal("100"),
            avg_cost=Decimal("150"),
            market_value=Decimal("17000"),
            current_price=Decimal("170"),
            day_pnl=Decimal("200"),
            unrealized_pnl=Decimal("2000"),
        ),
    ]
    return Portfolio(
        positions=positions,
        cash=Decimal("5000"),
        net_assets=Decimal("22000"),
        market_value=Decimal("17000"),
        day_pnl=Decimal("200"),
    )


class TestFormatHelpers:
    """Tests for formatting helper functions."""

    def test_format_money_positive(self):
        result = _format_money(1234.56)
        assert result == "+$1,234.56"

    def test_format_money_negative(self):
        result = _format_money(-500.0)
        assert result == "$-500.00"

    def test_format_money_zero(self):
        result = _format_money(0.0)
        assert result == "$0.00"

    def test_format_pct_positive(self):
        result = _format_pct(0.0523)
        assert result == "+5.23%"

    def test_format_pct_negative(self):
        result = _format_pct(-0.12)
        assert result == "-12.00%"

    def test_get_color_positive(self):
        assert _get_color(1.0) == "green"

    def test_get_color_negative(self):
        assert _get_color(-1.0) == "red"

    def test_get_color_zero(self):
        assert _get_color(0.0) == "white"


class TestConsoleFormatter:
    """Tests for ConsoleFormatter."""

    def test_print_portfolio(self):
        """Test portfolio printing."""
        if not RICH_AVAILABLE:
            return
        formatter = ConsoleFormatter()
        formatter.print_portfolio(_make_portfolio())

    def test_print_risk_metrics(self):
        """Test risk metrics printing."""
        if not RICH_AVAILABLE:
            return
        formatter = ConsoleFormatter()
        metrics = RiskMetrics(
            volatility_annualized=0.25,
            beta_spy=1.2,
            beta_qqq=1.3,
            sharpe_ratio=1.5,
            var_95=0.02,
            var_95_amount=Decimal("2000"),
            max_drawdown=0.10,
            hhi=0.15,
            high_corr_pairs=[("AAPL", "MSFT", 0.85)],
        )
        formatter.print_risk_metrics(metrics)

    def test_print_alerts_empty(self):
        """Test alerts printing with no alerts."""
        if not RICH_AVAILABLE:
            return
        formatter = ConsoleFormatter()
        formatter.print_alerts([])

    def test_print_alerts_with_data(self):
        """Test alerts printing with data."""
        if not RICH_AVAILABLE:
            return
        formatter = ConsoleFormatter()
        alerts = [
            Alert(
                type=AlertType.PRICE_MOVE,
                severity=AlertSeverity.WARNING,
                title="AAPL up 5%",
                message="Details here",
            ),
            Alert(
                type=AlertType.PNL_THRESHOLD,
                severity=AlertSeverity.CRITICAL,
                title="Portfolio P&L alert",
                message="Lost $1000",
            ),
        ]
        formatter.print_alerts(alerts)

    def test_print_history_empty(self):
        """Test history printing with no data."""
        if not RICH_AVAILABLE:
            return
        formatter = ConsoleFormatter()
        formatter.print_history([])

    def test_print_history_with_data(self):
        """Test history printing with data."""
        if not RICH_AVAILABLE:
            return
        formatter = ConsoleFormatter()
        snapshots = [
            PortfolioSnapshot(
                timestamp=datetime.now(),
                net_assets=100000,
                cash=5000,
                market_value=95000,
                day_pnl=500,
            ),
            PortfolioSnapshot(
                timestamp=datetime.now(),
                net_assets=101000,
                cash=5000,
                market_value=96000,
                day_pnl=-200,
            ),
        ]
        formatter.print_history(snapshots)

    def test_print_performance(self):
        """Test performance metrics printing."""
        if not RICH_AVAILABLE:
            return
        formatter = ConsoleFormatter()
        metrics = PerformanceMetrics(
            total_snapshots=30,
            first_date=datetime(2024, 1, 1),
            last_date=datetime(2024, 1, 30),
            starting_nav=100000,
            ending_nav=105000,
            total_return_pct=0.05,
            max_drawdown_pct=0.02,
            avg_daily_pnl=166.67,
            best_day_pnl=1000,
            worst_day_pnl=-500,
            positive_days=20,
            negative_days=10,
        )
        formatter.print_performance(metrics)

    def test_print_rebalance_empty(self):
        """Test rebalance printing with no actions."""
        if not RICH_AVAILABLE:
            return
        formatter = ConsoleFormatter()
        formatter.print_rebalance([])

    def test_print_rebalance_with_data(self):
        """Test rebalance printing with actions."""
        if not RICH_AVAILABLE:
            return
        formatter = ConsoleFormatter()
        actions = [
            RebalanceAction(
                ticker="TQQQ",
                current_weight=0.264,
                target_weight=0.20,
                deviation=0.064,
                status="OVERWEIGHT",
                dollar_amount=-2678,
                shares=-48,
            ),
            RebalanceAction(
                ticker="SPY",
                current_weight=0.081,
                target_weight=0.15,
                deviation=-0.069,
                status="UNDERWEIGHT",
                dollar_amount=2889,
                shares=6,
            ),
            RebalanceAction(
                ticker="QQQ",
                current_weight=0.302,
                target_weight=0.30,
                deviation=0.002,
                status="ON_TARGET",
                dollar_amount=0,
                shares=0,
            ),
        ]
        formatter.print_rebalance(actions)


class TestConvenienceFunctions:
    """Tests for module-level convenience functions."""

    def test_print_portfolio(self):
        """Test print_portfolio convenience function."""
        print_portfolio(_make_portfolio())

    def test_print_risk_metrics(self):
        """Test print_risk_metrics convenience function."""
        metrics = RiskMetrics(volatility_annualized=0.25)
        print_risk_metrics(metrics)
