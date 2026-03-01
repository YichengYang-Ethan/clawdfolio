"""Tests for CLI commands (v3 additions: history, rebalance, dashboard)."""

from unittest.mock import patch

from clawdfolio.cli.main import create_parser, main


class TestCreateParser:
    """Tests for CLI parser creation."""

    def test_parser_creation(self):
        """Test parser creates successfully."""
        parser = create_parser()
        assert parser is not None

    def test_history_subcommand(self):
        """Test history subcommand exists."""
        parser = create_parser()
        args = parser.parse_args(["history", "snapshot"])
        assert args.command == "history"
        assert args.history_command == "snapshot"

    def test_history_show_days(self):
        """Test history show --days flag."""
        parser = create_parser()
        args = parser.parse_args(["history", "show", "--days", "60"])
        assert args.history_command == "show"
        assert args.days == 60

    def test_history_performance(self):
        """Test history performance subcommand."""
        parser = create_parser()
        args = parser.parse_args(["history", "performance", "--days", "90"])
        assert args.history_command == "performance"
        assert args.days == 90

    def test_rebalance_subcommand(self):
        """Test rebalance subcommand."""
        parser = create_parser()
        args = parser.parse_args(["rebalance", "check"])
        assert args.command == "rebalance"
        assert args.rebalance_command == "check"

    def test_rebalance_propose(self):
        """Test rebalance propose --amount flag."""
        parser = create_parser()
        args = parser.parse_args(["rebalance", "propose", "--amount", "5000"])
        assert args.rebalance_command == "propose"
        assert args.amount == 5000.0

    def test_dashboard_subcommand(self):
        """Test dashboard subcommand."""
        parser = create_parser()
        args = parser.parse_args(["dashboard", "--port", "9999"])
        assert args.command == "dashboard"
        assert args.port == 9999

    def test_alerts_notify_flag(self):
        """Test --notify flag on alerts."""
        parser = create_parser()
        args = parser.parse_args(["alerts", "--notify"])
        assert args.notify is True

    def test_alerts_no_notify(self):
        """Test alerts without --notify."""
        parser = create_parser()
        args = parser.parse_args(["alerts"])
        assert args.notify is False


class TestHistoryCommand:
    """Tests for cmd_history."""

    @patch("clawdfolio.cli.main._get_portfolio")
    @patch("clawdfolio.cli.main.sys")
    def test_history_snapshot_json(self, mock_sys, mock_get_portfolio):
        """Test history snapshot with JSON output."""
        from decimal import Decimal

        from clawdfolio.core.types import Portfolio

        mock_get_portfolio.return_value = Portfolio(
            net_assets=Decimal("100000"),
            cash=Decimal("5000"),
            market_value=Decimal("95000"),
        )
        result = main(["--output", "json", "history", "snapshot"])
        assert result == 0

    def test_history_show_empty(self):
        """Test history show with no data."""
        with patch("clawdfolio.storage.repository.get_snapshots", return_value=[]):
            result = main(["history", "show"])
            assert result == 0

    def test_history_no_subcommand(self):
        """Test history without subcommand."""
        result = main(["history"])
        assert result == 1

    def test_history_performance_no_data(self):
        """Test performance with no snapshot data."""
        with patch("clawdfolio.storage.repository.get_performance", return_value=None):
            result = main(["history", "performance"])
            assert result == 1


class TestRebalanceCommand:
    """Tests for cmd_rebalance."""

    def test_rebalance_no_subcommand(self):
        """Test rebalance without subcommand."""
        result = main(["rebalance"])
        assert result == 1

    def test_rebalance_no_targets(self):
        """Test rebalance with no targets configured."""
        result = main(["rebalance", "check"])
        assert result == 1


class TestDashboardCommand:
    """Tests for cmd_dashboard."""

    def test_dashboard_no_streamlit(self):
        """Test dashboard without streamlit installed."""
        import sys

        # Temporarily make streamlit unimportable
        with patch.dict(sys.modules, {"streamlit": None}):
            result = main(["dashboard"])
            assert result == 1
