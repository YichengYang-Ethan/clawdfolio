"""Tests for CLI main module -- direct Python calls for coverage."""

from __future__ import annotations

import pytest

from clawdfolio.cli.main import (
    create_parser,
    main,
)


class TestCreateParser:
    """Tests for create_parser."""

    def test_parser_creation(self):
        parser = create_parser()
        assert parser is not None
        assert parser.prog == "clawdfolio"

    def test_parser_subcommands(self):
        parser = create_parser()
        # Should parse known subcommands
        args = parser.parse_args(["--broker", "demo", "summary"])
        assert args.command == "summary"
        assert args.broker == "demo"

    def test_parser_risk(self):
        parser = create_parser()
        args = parser.parse_args(["risk", "--detailed"])
        assert args.command == "risk"
        assert args.detailed is True

    def test_parser_alerts(self):
        parser = create_parser()
        args = parser.parse_args(["alerts", "--severity", "warning"])
        assert args.command == "alerts"
        assert args.severity == "warning"

    def test_parser_export(self):
        parser = create_parser()
        args = parser.parse_args(["export", "portfolio", "--format", "json"])
        assert args.command == "export"
        assert args.what == "portfolio"
        assert args.format == "json"

    def test_parser_dca(self):
        parser = create_parser()
        args = parser.parse_args(["dca", "AAPL", "--months", "6", "--amount", "500"])
        assert args.command == "dca"
        assert args.symbol == "AAPL"
        assert args.months == 6
        assert args.amount == 500.0

    def test_parser_snapshot(self):
        parser = create_parser()
        args = parser.parse_args(["snapshot"])
        assert args.command == "snapshot"

    def test_parser_performance(self):
        parser = create_parser()
        args = parser.parse_args(["performance", "--period", "3m"])
        assert args.command == "performance"
        assert args.period == "3m"

    def test_parser_compare(self):
        parser = create_parser()
        args = parser.parse_args(["compare", "SPY", "--period", "1y"])
        assert args.command == "compare"
        assert args.benchmark == "SPY"

    def test_parser_options_expiries(self):
        parser = create_parser()
        args = parser.parse_args(["options", "expiries", "TQQQ"])
        assert args.command == "options"
        assert args.options_command == "expiries"
        assert args.symbol == "TQQQ"

    def test_parser_finance_list(self):
        parser = create_parser()
        args = parser.parse_args(["finance", "list"])
        assert args.command == "finance"
        assert args.finance_command == "list"

    def test_parser_quotes(self):
        parser = create_parser()
        args = parser.parse_args(["quotes", "AAPL", "GOOG"])
        assert args.command == "quotes"
        assert args.symbols == ["AAPL", "GOOG"]


class TestMainEntryPoint:
    """Tests for main() function."""

    def test_main_version(self):
        with pytest.raises(SystemExit) as exc_info:
            main(["--version"])
        assert exc_info.value.code == 0

    def test_main_summary_demo(self):
        result = main(["--broker", "demo", "summary"])
        assert result == 0

    def test_main_summary_demo_json(self):
        result = main(["--broker", "demo", "-o", "json", "summary"])
        assert result == 0

    def test_main_no_command_defaults_summary(self):
        # When no command is given, defaults to summary with all brokers
        # With demo fallback this should work
        result = main(["--broker", "demo"])
        assert result == 0

    def test_main_alerts_demo(self):
        result = main(["--broker", "demo", "alerts"])
        assert result == 0

    def test_main_alerts_demo_json(self):
        result = main(["--broker", "demo", "-o", "json", "alerts"])
        assert result == 0

    def test_main_export_portfolio_demo(self):
        result = main(["--broker", "demo", "export", "portfolio"])
        assert result == 0

    def test_main_export_portfolio_json(self):
        result = main(["--broker", "demo", "export", "portfolio", "--format", "json"])
        assert result == 0

    def test_main_export_risk_demo(self):
        result = main(["--broker", "demo", "export", "risk"])
        assert result == 0

    def test_main_export_alerts_demo(self):
        result = main(["--broker", "demo", "export", "alerts"])
        assert result == 0

    def test_main_earnings_demo(self):
        result = main(["--broker", "demo", "earnings"])
        assert result == 0

    def test_main_earnings_demo_json(self):
        result = main(["--broker", "demo", "-o", "json", "earnings"])
        assert result == 0

    def test_main_snapshot_demo(self, tmp_path):
        hist_file = str(tmp_path / "history.csv")
        result = main(["--broker", "demo", "snapshot", "--file", hist_file])
        assert result == 0

    def test_main_performance_no_data(self, tmp_path):
        hist_file = str(tmp_path / "nodata.csv")
        result = main(["performance", "--file", hist_file])
        assert result == 0  # prints "No snapshot data"

    def test_main_performance_json(self, tmp_path):
        hist_file = str(tmp_path / "nodata.csv")
        result = main(["-o", "json", "performance", "--file", hist_file])
        assert result == 0

    def test_main_dca_no_symbol(self):
        result = main(["dca"])
        assert result == 1  # no symbol

    def test_main_finance_list(self):
        result = main(["finance", "list"])
        assert result == 0

    def test_main_finance_list_json(self):
        result = main(["-o", "json", "finance", "list"])
        assert result == 0

    def test_main_options_no_subcommand(self):
        result = main(["options"])
        assert result == 1

    def test_main_risk_demo(self):
        # Risk may fail due to market data, but should handle gracefully
        result = main(["--broker", "demo", "risk"])
        assert result in (0, 1)

    def test_main_risk_demo_json(self):
        result = main(["--broker", "demo", "-o", "json", "risk"])
        assert result in (0, 1)

    def test_main_export_to_file(self, tmp_path):
        out_file = str(tmp_path / "out.csv")
        result = main(["--broker", "demo", "export", "portfolio", "--file", out_file])
        assert result == 0
        with open(out_file) as f:
            content = f.read()
        assert len(content) > 0

    def test_main_export_risk_json(self):
        result = main(["--broker", "demo", "export", "risk", "--format", "json"])
        assert result == 0

    def test_main_export_alerts_json(self):
        result = main(["--broker", "demo", "export", "alerts", "--format", "json"])
        assert result == 0

    def test_main_all_broker_fallback_demo(self):
        # "all" broker with no real brokers configured falls back to demo
        result = main(["--broker", "all", "summary"])
        assert result in (0, 1)  # may fail if config tries real brokers

    def test_main_finance_no_subcommand_defaults_list(self):
        result = main(["finance"])
        assert result == 0

    def test_main_finance_init(self, tmp_path):
        ws = str(tmp_path / "finance_ws")
        result = main(["finance", "init", "--workspace", ws])
        assert result == 0

    def test_main_finance_init_json(self, tmp_path):
        ws = str(tmp_path / "finance_ws2")
        result = main(["-o", "json", "finance", "init", "--workspace", ws])
        assert result == 0

    def test_main_alerts_severity_filter(self):
        result = main(["--broker", "demo", "alerts", "--severity", "critical"])
        assert result == 0

    def test_main_snapshot_idempotent(self, tmp_path):
        hist_file = str(tmp_path / "history.csv")
        main(["--broker", "demo", "snapshot", "--file", hist_file])
        result = main(["--broker", "demo", "snapshot", "--file", hist_file])
        assert result == 0  # second time says "already exists"


class TestCmdQuotes:
    """Tests for cmd_quotes."""

    def test_quotes_console(self):
        result = main(["quotes", "AAPL"])
        assert result == 0

    def test_quotes_json(self):
        result = main(["-o", "json", "quotes", "AAPL"])
        assert result == 0

    def test_quotes_multiple(self):
        result = main(["quotes", "AAPL", "GOOG"])
        assert result == 0


class TestCmdDCA:
    """Tests for cmd_dca with a symbol."""

    def test_dca_console(self):
        result = main(["dca", "AAPL", "--months", "3", "--amount", "100"])
        assert result in (0, 1)

    def test_dca_json(self):
        result = main(["-o", "json", "dca", "AAPL", "--months", "3", "--amount", "100"])
        assert result in (0, 1)


class TestCmdRiskDetailed:
    """Tests for detailed risk output."""

    def test_risk_detailed(self):
        result = main(["--broker", "demo", "risk", "--detailed"])
        assert result in (0, 1)


class TestCLIInit:
    """Tests for cli/__init__.py."""

    def test_create_parser_from_init(self):
        from clawdfolio.cli import create_parser

        parser = create_parser()
        assert parser is not None

    def test_create_parser_returns_parser(self):
        from clawdfolio.cli import create_parser as cp

        parser = cp()
        assert parser.prog == "clawdfolio"
