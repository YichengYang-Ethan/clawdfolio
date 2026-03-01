"""Tests for DCA strategy module."""

from unittest.mock import patch

import pandas as pd

from clawdfolio.strategies.dca import DCAStrategy, calculate_dca_performance


class TestDcaPerformance:
    """Tests for calculate_dca_performance."""

    @patch("clawdfolio.strategies.dca.get_price", return_value=130.0)
    @patch("clawdfolio.strategies.dca.get_history")
    def test_basic_dca(self, mock_history, mock_price):
        dates = pd.date_range("2024-01-01", periods=60, freq="B")
        prices = pd.DataFrame({"Close": [100 + i * 0.5 for i in range(60)]}, index=dates)
        mock_history.return_value = prices

        result = calculate_dca_performance("AAPL", monthly_amount=1000.0, months=2)
        assert result is not None
        assert result["total_invested"] > 0
        assert result["total_shares"] > 0
        assert result["ticker"] == "AAPL"

    @patch("clawdfolio.strategies.dca.get_history")
    def test_dca_empty_data(self, mock_history):
        mock_history.return_value = pd.DataFrame()
        result = calculate_dca_performance("FAKE", monthly_amount=1000.0, months=6)
        assert result == {}

    @patch("clawdfolio.strategies.dca.get_price", return_value=None)
    @patch("clawdfolio.strategies.dca.get_history")
    def test_dca_no_current_price(self, mock_history, mock_price):
        dates = pd.date_range("2024-01-01", periods=30, freq="B")
        prices = pd.DataFrame({"Close": [100.0] * 30}, index=dates)
        mock_history.return_value = prices

        result = calculate_dca_performance("AAPL", monthly_amount=500.0, months=1)
        assert result is not None
        # Falls back to last price in history
        assert result["current_price"] == 100.0


class TestDCAStrategy:
    """Tests for DCAStrategy class."""

    def test_get_regular_allocation(self):
        strategy = DCAStrategy(
            targets={"QQQ": 0.5, "SPY": 0.3, "BND": 0.2},
            monthly_amount=2000.0,
        )
        alloc = strategy.get_regular_allocation()
        assert alloc["QQQ"] == 1000.0
        assert alloc["SPY"] == 600.0
        assert alloc["BND"] == 400.0
