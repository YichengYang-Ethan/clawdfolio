"""Tests for options and finance CLI commands."""

from argparse import Namespace
from unittest.mock import patch

from clawdfolio.cli.main import cmd_finance, cmd_options


class TestCmdOptions:
    """Tests for cmd_options."""

    def test_options_no_subcommand(self):
        args = Namespace(output="console", options_command=None, config=None)
        result = cmd_options(args)
        assert result == 1

    def test_options_unknown_subcommand(self):
        args = Namespace(output="console", options_command="unknown", config=None)
        result = cmd_options(args)
        assert result == 1

    @patch("clawdfolio.market.data.get_option_expiries", return_value=["2024-03-15", "2024-04-19"])
    def test_options_expiries_console(self, mock_exp):
        args = Namespace(output="console", options_command="expiries", symbol="TQQQ", config=None)
        result = cmd_options(args)
        assert result == 0

    @patch("clawdfolio.market.data.get_option_expiries", return_value=["2024-03-15"])
    def test_options_expiries_json(self, mock_exp):
        args = Namespace(output="json", options_command="expiries", symbol="TQQQ", config=None)
        result = cmd_options(args)
        assert result == 0

    @patch("clawdfolio.market.data.get_option_expiries", return_value=[])
    def test_options_expiries_empty(self, mock_exp):
        args = Namespace(output="console", options_command="expiries", symbol="FAKE", config=None)
        result = cmd_options(args)
        assert result == 0

    @patch("clawdfolio.market.data.get_option_quote", return_value=None)
    def test_options_quote_not_found(self, mock_quote):
        args = Namespace(
            output="console", options_command="quote", symbol="TQQQ",
            expiry="2024-03-15", strike=50.0, option_type="C", config=None,
        )
        result = cmd_options(args)
        assert result == 1

    @patch("clawdfolio.market.data.get_option_chain", return_value=None)
    def test_options_chain_not_found(self, mock_chain):
        args = Namespace(
            output="console", options_command="chain", symbol="TQQQ",
            expiry="2024-03-15", side="both", limit=10, config=None,
        )
        result = cmd_options(args)
        assert result == 1


class TestCmdFinance:
    """Tests for cmd_finance."""

    def test_finance_list_console(self):
        args = Namespace(
            output="console", finance_command=None,
            broker="demo", config=None,
        )
        result = cmd_finance(args)
        assert result == 0

    def test_finance_list_json(self):
        args = Namespace(
            output="json", finance_command="list",
            broker="demo", config=None, category=None,
        )
        result = cmd_finance(args)
        assert result == 0

    def test_finance_unknown_subcommand(self):
        args = Namespace(
            output="console", finance_command="unknown_xyz",
            broker="demo", config=None,
        )
        result = cmd_finance(args)
        assert result == 1

    def test_finance_run_missing_workflow(self):
        args = Namespace(
            output="console", finance_command="run",
            workflow="nonexistent_workflow_123",
            workspace=None, sync=False, script_args=[],
            broker="demo", config=None,
        )
        result = cmd_finance(args)
        assert result == 1

    def test_finance_init(self):
        args = Namespace(
            output="console", finance_command="init",
            workspace=None, sync=False,
            broker="demo", config=None,
        )
        result = cmd_finance(args)
        assert result == 0

    def test_finance_init_json(self):
        args = Namespace(
            output="json", finance_command="init",
            workspace=None, sync=False,
            broker="demo", config=None,
        )
        result = cmd_finance(args)
        assert result == 0
