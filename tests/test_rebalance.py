"""Tests for rebalance module."""

from decimal import Decimal

import pytest

from clawdfolio.core.types import Portfolio, Position, Symbol
from clawdfolio.strategies.rebalance import (
    TargetAllocation,
    calculate_rebalance,
    propose_dca_allocation,
)


@pytest.fixture
def sample_portfolio():
    """Create a sample portfolio for rebalance testing."""
    positions = [
        Position(
            symbol=Symbol(ticker="QQQ"),
            quantity=Decimal("100"),
            avg_cost=Decimal("350"),
            market_value=Decimal("40000"),
            current_price=Decimal("400"),
        ),
        Position(
            symbol=Symbol(ticker="VOO"),
            quantity=Decimal("50"),
            avg_cost=Decimal("400"),
            market_value=Decimal("22500"),
            current_price=Decimal("450"),
        ),
        Position(
            symbol=Symbol(ticker="TQQQ"),
            quantity=Decimal("200"),
            avg_cost=Decimal("50"),
            market_value=Decimal("37500"),
            current_price=Decimal("187.50"),
        ),
    ]
    return Portfolio(
        positions=positions,
        cash=Decimal("0"),
        net_assets=Decimal("100000"),
        market_value=Decimal("100000"),
    )


@pytest.fixture
def targets():
    """Standard target allocations."""
    return [
        TargetAllocation(ticker="QQQ", weight=0.30),
        TargetAllocation(ticker="VOO", weight=0.25),
        TargetAllocation(ticker="TQQQ", weight=0.20),
    ]


class TestCalculateRebalance:
    """Tests for calculate_rebalance."""

    def test_basic_rebalance(self, sample_portfolio, targets):
        """Test basic rebalance calculation."""
        actions = calculate_rebalance(sample_portfolio, targets)
        assert len(actions) == 3
        # TQQQ is most overweight (37.5% vs 20%)
        assert actions[0].ticker == "TQQQ"
        assert actions[0].status == "OVERWEIGHT"

    def test_on_target(self, sample_portfolio):
        """Test position within tolerance is ON_TARGET."""
        targets = [TargetAllocation(ticker="QQQ", weight=0.40)]
        actions = calculate_rebalance(sample_portfolio, targets, tolerance=0.03)
        assert actions[0].status == "ON_TARGET"

    def test_underweight(self, sample_portfolio):
        """Test underweight detection."""
        targets = [TargetAllocation(ticker="VOO", weight=0.50)]
        actions = calculate_rebalance(sample_portfolio, targets)
        assert actions[0].status == "UNDERWEIGHT"
        assert actions[0].dollar_amount > 0  # Need to buy

    def test_overweight(self, sample_portfolio):
        """Test overweight detection."""
        targets = [TargetAllocation(ticker="QQQ", weight=0.10)]
        actions = calculate_rebalance(sample_portfolio, targets)
        assert actions[0].status == "OVERWEIGHT"
        assert actions[0].dollar_amount < 0  # Need to sell

    def test_empty_portfolio(self, targets):
        """Test with empty portfolio."""
        portfolio = Portfolio(net_assets=Decimal("0"))
        actions = calculate_rebalance(portfolio, targets)
        assert actions == []

    def test_missing_position(self, sample_portfolio):
        """Test target for position not in portfolio."""
        targets = [TargetAllocation(ticker="SPY", weight=0.15)]
        actions = calculate_rebalance(sample_portfolio, targets)
        assert len(actions) == 1
        assert actions[0].ticker == "SPY"
        assert actions[0].current_weight == 0.0
        assert actions[0].status == "UNDERWEIGHT"

    def test_sorted_by_deviation(self, sample_portfolio, targets):
        """Test actions are sorted by absolute deviation."""
        actions = calculate_rebalance(sample_portfolio, targets)
        deviations = [abs(a.deviation) for a in actions]
        assert deviations == sorted(deviations, reverse=True)

    def test_shares_calculation(self, sample_portfolio, targets):
        """Test approximate share count calculation."""
        actions = calculate_rebalance(sample_portfolio, targets)
        for a in actions:
            # Shares should be an integer
            assert isinstance(a.shares, int)

    def test_single_position(self):
        """Test with only one position."""
        portfolio = Portfolio(
            positions=[
                Position(
                    symbol=Symbol(ticker="AAPL"),
                    quantity=Decimal("10"),
                    market_value=Decimal("10000"),
                    current_price=Decimal("1000"),
                )
            ],
            net_assets=Decimal("10000"),
            market_value=Decimal("10000"),
        )
        targets = [TargetAllocation(ticker="AAPL", weight=0.50)]
        actions = calculate_rebalance(portfolio, targets)
        assert actions[0].status == "OVERWEIGHT"  # 100% vs 50%

    def test_100_percent_deviation(self):
        """Test portfolio fully in one stock, target is zero."""
        portfolio = Portfolio(
            positions=[
                Position(
                    symbol=Symbol(ticker="AAPL"),
                    quantity=Decimal("10"),
                    market_value=Decimal("10000"),
                    current_price=Decimal("1000"),
                )
            ],
            net_assets=Decimal("10000"),
            market_value=Decimal("10000"),
        )
        targets = [TargetAllocation(ticker="AAPL", weight=0.0)]
        actions = calculate_rebalance(portfolio, targets)
        assert actions[0].deviation == pytest.approx(1.0)


class TestProposeDcaAllocation:
    """Tests for propose_dca_allocation."""

    def test_basic_proposal(self, sample_portfolio, targets):
        """Test basic DCA allocation proposal."""
        actions = propose_dca_allocation(sample_portfolio, targets, amount=5000)
        # Should only suggest buys
        for a in actions:
            assert a.dollar_amount > 0
            assert a.status == "BUY"

    def test_zero_amount(self, sample_portfolio, targets):
        """Test with zero investment amount."""
        actions = propose_dca_allocation(sample_portfolio, targets, amount=0)
        assert actions == []

    def test_empty_portfolio(self, targets):
        """Test DCA with empty portfolio."""
        portfolio = Portfolio(net_assets=Decimal("0"))
        actions = propose_dca_allocation(portfolio, targets, amount=5000)
        assert actions == []

    def test_total_allocation_matches_amount(self, sample_portfolio, targets):
        """Test that total allocation approximately equals the investment amount."""
        amount = 5000.0
        actions = propose_dca_allocation(sample_portfolio, targets, amount=amount)
        total = sum(a.dollar_amount for a in actions)
        assert total == pytest.approx(amount, abs=1)

    def test_sorted_by_amount(self, sample_portfolio, targets):
        """Test proposals sorted by dollar amount descending."""
        actions = propose_dca_allocation(sample_portfolio, targets, amount=5000)
        amounts = [a.dollar_amount for a in actions]
        assert amounts == sorted(amounts, reverse=True)
