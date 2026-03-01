"""Extended CLI tests for better coverage."""

from argparse import Namespace
from decimal import Decimal
from unittest.mock import patch

import pytest

from clawdfolio.cli.main import (
    cmd_alerts,
    cmd_dca,
    cmd_earnings,
    cmd_quotes,
    cmd_risk,
    cmd_summary,
    main,
)
from clawdfolio.core.types import Portfolio, Position, Quote, Symbol


def _mock_portfolio():
    """Build a mock portfolio."""
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
        day_pnl_pct=0.009,
        source="test",
    )


class TestMainEntrypoint:
    """Tests for main() function dispatch."""

    def test_default_command_is_summary(self):
        """Test default command when none specified."""
        with patch("clawdfolio.cli.main.cmd_summary", return_value=0) as mock:
            main([])
            mock.assert_called_once()

    def test_version_flag(self):
        """Test --version flag."""
        with pytest.raises(SystemExit) as exc_info:
            main(["--version"])
        assert exc_info.value.code == 0


class TestCmdSummary:
    """Tests for cmd_summary."""

    @patch("clawdfolio.cli.main._get_portfolio")
    def test_summary_console(self, mock_get):
        mock_get.return_value = _mock_portfolio()
        args = Namespace(output="console", broker="demo", config=None, top=10)
        result = cmd_summary(args)
        assert result == 0

    @patch("clawdfolio.cli.main._get_portfolio")
    def test_summary_json(self, mock_get):
        mock_get.return_value = _mock_portfolio()
        args = Namespace(output="json", broker="demo", config=None, top=10)
        result = cmd_summary(args)
        assert result == 0

    @patch("clawdfolio.cli.main._get_portfolio", side_effect=Exception("fail"))
    def test_summary_error(self, mock_get):
        args = Namespace(output="console", broker="demo", config=None, top=10)
        result = cmd_summary(args)
        assert result == 1


class TestCmdQuotes:
    """Tests for cmd_quotes."""

    @patch("clawdfolio.market.data.get_quotes_yfinance")
    def test_quotes_console(self, mock_quotes):
        mock_quotes.return_value = {
            "AAPL": Quote(
                symbol=Symbol(ticker="AAPL"),
                price=Decimal("170"),
                prev_close=Decimal("168"),
            ),
        }
        args = Namespace(output="console", symbols=["AAPL"])
        result = cmd_quotes(args)
        assert result == 0

    @patch("clawdfolio.market.data.get_quotes_yfinance")
    def test_quotes_json(self, mock_quotes):
        mock_quotes.return_value = {
            "AAPL": Quote(
                symbol=Symbol(ticker="AAPL"),
                price=Decimal("170"),
                prev_close=Decimal("168"),
            ),
        }
        args = Namespace(output="json", symbols=["AAPL"])
        result = cmd_quotes(args)
        assert result == 0


class TestCmdRisk:
    """Tests for cmd_risk."""

    @patch("clawdfolio.analysis.risk.analyze_risk")
    @patch("clawdfolio.cli.main._get_portfolio")
    def test_risk_console(self, mock_get, mock_risk):
        from clawdfolio.core.types import RiskMetrics

        mock_get.return_value = _mock_portfolio()
        mock_risk.return_value = RiskMetrics(
            volatility_annualized=0.25,
            beta_spy=1.2,
            sharpe_ratio=1.5,
        )
        args = Namespace(output="console", broker="demo", config=None, detailed=False)
        result = cmd_risk(args)
        assert result == 0

    @patch("clawdfolio.analysis.risk.analyze_risk")
    @patch("clawdfolio.cli.main._get_portfolio")
    def test_risk_json(self, mock_get, mock_risk):
        from clawdfolio.core.types import RiskMetrics

        mock_get.return_value = _mock_portfolio()
        mock_risk.return_value = RiskMetrics(
            volatility_annualized=0.25,
            beta_spy=1.2,
            sharpe_ratio=1.5,
        )
        args = Namespace(output="json", broker="demo", config=None, detailed=False)
        result = cmd_risk(args)
        assert result == 0

    @patch("clawdfolio.cli.main._get_portfolio", side_effect=Exception("fail"))
    def test_risk_error(self, mock_get):
        args = Namespace(output="console", broker="demo", config=None, detailed=False)
        result = cmd_risk(args)
        assert result == 1


class TestCmdAlerts:
    """Tests for cmd_alerts."""

    @patch("clawdfolio.cli.main._get_portfolio")
    def test_alerts_no_alerts(self, mock_get):
        mock_get.return_value = _mock_portfolio()
        args = Namespace(
            output="console",
            broker="demo",
            config=None,
            severity=None,
            notify=False,
        )
        result = cmd_alerts(args)
        assert result == 0

    @patch("clawdfolio.cli.main._get_portfolio")
    def test_alerts_json(self, mock_get):
        mock_get.return_value = _mock_portfolio()
        args = Namespace(
            output="json",
            broker="demo",
            config=None,
            severity=None,
            notify=False,
        )
        result = cmd_alerts(args)
        assert result == 0

    @patch("clawdfolio.cli.main._get_portfolio", side_effect=Exception("fail"))
    def test_alerts_error(self, mock_get):
        args = Namespace(
            output="console",
            broker="demo",
            config=None,
            severity=None,
            notify=False,
        )
        result = cmd_alerts(args)
        assert result == 1


class TestCmdEarnings:
    """Tests for cmd_earnings."""

    @patch("clawdfolio.monitors.earnings.get_upcoming_earnings", return_value=[])
    @patch("clawdfolio.cli.main._get_portfolio")
    def test_earnings_console(self, mock_get, mock_earnings):
        mock_get.return_value = _mock_portfolio()
        args = Namespace(output="console", broker="demo", config=None, days=14)
        result = cmd_earnings(args)
        assert result == 0

    @patch("clawdfolio.monitors.earnings.get_upcoming_earnings", return_value=[])
    @patch("clawdfolio.cli.main._get_portfolio")
    def test_earnings_json(self, mock_get, mock_earnings):
        mock_get.return_value = _mock_portfolio()
        args = Namespace(output="json", broker="demo", config=None, days=14)
        result = cmd_earnings(args)
        assert result == 0

    @patch("clawdfolio.cli.main._get_portfolio", side_effect=Exception("fail"))
    def test_earnings_error(self, mock_get):
        args = Namespace(output="console", broker="demo", config=None, days=14)
        result = cmd_earnings(args)
        assert result == 1


class TestCmdDca:
    """Tests for cmd_dca."""

    def test_dca_no_symbol(self):
        args = Namespace(output="console", symbol=None, months=12, amount=1000.0)
        result = cmd_dca(args)
        assert result == 1


class TestCmdHistoryExtended:
    """Extended history command tests."""

    @patch("clawdfolio.cli.main._get_portfolio")
    def test_history_snapshot_console(self, mock_get):
        mock_get.return_value = _mock_portfolio()
        result = main(["history", "snapshot"])
        assert result == 0

    @patch("clawdfolio.storage.repository.get_snapshots")
    def test_history_show_json(self, mock_snaps):
        from datetime import datetime

        from clawdfolio.storage.models import PortfolioSnapshot

        mock_snaps.return_value = [
            PortfolioSnapshot(
                timestamp=datetime.now(),
                net_assets=100000,
                cash=5000,
                market_value=95000,
                day_pnl=500,
            )
        ]
        result = main(["--output", "json", "history", "show"])
        assert result == 0

    @patch("clawdfolio.storage.repository.get_performance")
    def test_history_performance_json(self, mock_perf):
        from datetime import datetime

        from clawdfolio.storage.models import PerformanceMetrics

        mock_perf.return_value = PerformanceMetrics(
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
        result = main(["--output", "json", "history", "performance"])
        assert result == 0

    @patch("clawdfolio.storage.repository.get_performance", return_value=None)
    def test_history_performance_no_data(self, mock_perf):
        result = main(["history", "performance"])
        assert result == 1

    def test_history_no_subcommand(self):
        result = main(["history"])
        assert result == 1


class TestCmdRebalanceExtended:
    """Extended rebalance command tests."""

    def test_rebalance_no_subcommand(self):
        result = main(["rebalance"])
        assert result == 1

    def test_rebalance_no_targets(self):
        result = main(["rebalance", "check"])
        assert result == 1

    @patch("clawdfolio.cli.main._get_portfolio")
    @patch("clawdfolio.core.config.load_config")
    def test_rebalance_check_json(self, mock_config, mock_get):
        from clawdfolio.core.config import (
            Config,
            RebalanceTarget,
            RebalancingConfig,
        )

        mock_get.return_value = _mock_portfolio()
        mock_config.return_value = Config(
            rebalancing=RebalancingConfig(
                tolerance=0.03,
                targets=[RebalanceTarget(ticker="AAPL", weight=0.50)],
            )
        )
        result = main(["--output", "json", "rebalance", "check"])
        assert result == 0

    @patch("clawdfolio.cli.main._get_portfolio")
    @patch("clawdfolio.core.config.load_config")
    def test_rebalance_propose_json(self, mock_config, mock_get):
        from clawdfolio.core.config import (
            Config,
            RebalanceTarget,
            RebalancingConfig,
        )

        mock_get.return_value = _mock_portfolio()
        mock_config.return_value = Config(
            rebalancing=RebalancingConfig(
                tolerance=0.03,
                targets=[RebalanceTarget(ticker="AAPL", weight=0.50)],
            )
        )
        result = main(["--output", "json", "rebalance", "propose", "--amount", "5000"])
        assert result == 0


class TestCmdDashboard:
    """Tests for cmd_dashboard."""

    def test_dashboard_no_streamlit(self):
        import sys

        with patch.dict(sys.modules, {"streamlit": None}):
            result = main(["dashboard"])
            assert result == 1
