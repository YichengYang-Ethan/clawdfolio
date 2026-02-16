"""Tests for DCA strategy."""

from decimal import Decimal
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest

from clawdfolio.core.types import Exchange, Portfolio, Position, Symbol
from clawdfolio.strategies.dca import (
    DCAStrategy,
    SignalType,
    calculate_dca_performance,
    check_dca_signals,
)


def _make_position(ticker, weight=0.10, market_value=10000, current_price=100.0):
    pos = Position(
        symbol=Symbol(ticker=ticker, exchange=Exchange.NYSE),
        quantity=Decimal("100"),
        market_value=Decimal(str(market_value)),
        current_price=Decimal(str(current_price)),
    )
    pos.weight = weight
    return pos


def _make_portfolio(positions, net_assets=100000):
    return Portfolio(
        positions=positions,
        net_assets=Decimal(str(net_assets)),
        market_value=Decimal(str(net_assets)),
    )


class TestDCAStrategy:
    def test_rebalance_signal(self):
        """Under-weight position should trigger rebalance signal."""
        strategy = DCAStrategy(
            targets={"AAPL": 0.30},
            rebalance_threshold=0.05,
        )
        pos = _make_position("AAPL", weight=0.20, current_price=150.0)
        portfolio = _make_portfolio([pos])

        with patch("clawdfolio.strategies.dca.get_history") as mock_hist:
            mock_hist.return_value = pd.DataFrame()  # No dip data
            signals = strategy.check_signals(portfolio)

        rebalance = [s for s in signals if s.signal_type == SignalType.REBALANCE]
        assert len(rebalance) == 1
        assert rebalance[0].ticker == "AAPL"
        assert rebalance[0].suggested_amount > 0

    def test_no_rebalance_within_threshold(self):
        """Position within threshold should not trigger rebalance."""
        strategy = DCAStrategy(
            targets={"AAPL": 0.30},
            rebalance_threshold=0.05,
        )
        pos = _make_position("AAPL", weight=0.28, market_value=28000, current_price=150.0)
        portfolio = _make_portfolio([pos])

        with patch("clawdfolio.strategies.dca.get_history") as mock_hist:
            mock_hist.return_value = pd.DataFrame()
            signals = strategy.check_signals(portfolio)

        rebalance = [s for s in signals if s.signal_type == SignalType.REBALANCE]
        assert len(rebalance) == 0

    @patch("clawdfolio.strategies.dca.get_history")
    def test_dip_signal(self, mock_hist):
        """Position down from recent high should trigger dip signal."""
        # Create price data with a dip
        dates = pd.date_range("2025-01-01", periods=60, freq="B")
        prices = [100.0] * 30 + [85.0] * 30  # 15% drop
        df = pd.DataFrame({"Close": prices}, index=dates)
        mock_hist.return_value = df

        strategy = DCAStrategy(
            targets={"AAPL": 0.30},
            dip_threshold=0.10,
            rebalance_threshold=0.05,
        )
        pos = _make_position("AAPL", weight=0.28, current_price=85.0)
        portfolio = _make_portfolio([pos])
        signals = strategy.check_signals(portfolio)

        dip_signals = [s for s in signals if s.signal_type == SignalType.DIP]
        assert len(dip_signals) == 1
        assert "15.0%" in dip_signals[0].reason

    def test_get_regular_allocation(self):
        """Regular allocation should split by target weights."""
        strategy = DCAStrategy(
            targets={"AAPL": 0.50, "MSFT": 0.30, "GOOG": 0.20},
            monthly_amount=1000.0,
        )
        alloc = strategy.get_regular_allocation()
        assert alloc["AAPL"] == pytest.approx(500.0)
        assert alloc["MSFT"] == pytest.approx(300.0)
        assert alloc["GOOG"] == pytest.approx(200.0)


class TestCheckDCASignals:
    @patch("clawdfolio.strategies.dca.get_history")
    def test_convenience_function(self, mock_hist):
        """check_dca_signals should wrap DCAStrategy."""
        mock_hist.return_value = pd.DataFrame()
        pos = _make_position("AAPL", weight=0.10, current_price=150.0)
        portfolio = _make_portfolio([pos])
        signals = check_dca_signals(portfolio, targets={"AAPL": 0.30})
        assert isinstance(signals, list)


class TestCalculateDCAPerformance:
    @patch("clawdfolio.strategies.dca.get_price")
    @patch("clawdfolio.strategies.dca.get_history")
    def test_basic_performance(self, mock_hist, mock_price):
        """Should calculate DCA performance metrics."""
        dates = pd.date_range("2025-01-01", periods=180, freq="B")
        prices = pd.Series(
            np.linspace(100, 120, len(dates)),
            index=dates,
            name="Close",
        )
        df = pd.DataFrame({"Close": prices})
        mock_hist.return_value = df
        mock_price.return_value = 120.0

        result = calculate_dca_performance("AAPL", monthly_amount=1000.0, months=6)
        assert result
        assert result["ticker"] == "AAPL"
        assert result["total_invested"] > 0
        assert result["total_shares"] > 0
        assert "current_value" in result
        assert "total_return_pct" in result

    @patch("clawdfolio.strategies.dca.get_history")
    def test_empty_history(self, mock_hist):
        """Empty history should return empty dict."""
        mock_hist.return_value = pd.DataFrame()
        result = calculate_dca_performance("INVALID", monthly_amount=1000.0)
        assert result == {}
