"""Edge case tests for rebalance module."""

from decimal import Decimal

from clawdfolio.core.types import Portfolio, Position, Symbol
from clawdfolio.strategies.rebalance import (
    TargetAllocation,
    calculate_rebalance,
    propose_dca_allocation,
)


class TestRebalanceEdgeCases:
    """Edge case tests for rebalancing."""

    def test_empty_targets(self):
        """Test with no targets."""
        portfolio = Portfolio(
            positions=[
                Position(
                    symbol=Symbol(ticker="AAPL"),
                    quantity=Decimal("10"),
                    market_value=Decimal("1000"),
                    current_price=Decimal("100"),
                )
            ],
            net_assets=Decimal("1000"),
            market_value=Decimal("1000"),
        )
        actions = calculate_rebalance(portfolio, [])
        assert actions == []

    def test_zero_net_assets(self):
        """Test with zero net assets."""
        portfolio = Portfolio(net_assets=Decimal("0"))
        targets = [TargetAllocation(ticker="AAPL", weight=0.5)]
        actions = calculate_rebalance(portfolio, targets)
        assert actions == []

    def test_negative_net_assets(self):
        """Test with negative net assets (margin)."""
        portfolio = Portfolio(net_assets=Decimal("-1000"))
        targets = [TargetAllocation(ticker="AAPL", weight=0.5)]
        actions = calculate_rebalance(portfolio, targets)
        assert actions == []

    def test_zero_price_position(self):
        """Test with a position that has zero price."""
        portfolio = Portfolio(
            positions=[
                Position(
                    symbol=Symbol(ticker="PENNY"),
                    quantity=Decimal("1000"),
                    market_value=Decimal("0"),
                    current_price=Decimal("0"),
                )
            ],
            net_assets=Decimal("10000"),
            market_value=Decimal("10000"),
        )
        targets = [TargetAllocation(ticker="PENNY", weight=0.10)]
        actions = calculate_rebalance(portfolio, targets)
        assert len(actions) == 1
        assert actions[0].shares == 0  # Can't calculate shares with zero price

    def test_very_small_tolerance(self):
        """Test with extremely small tolerance."""
        portfolio = Portfolio(
            positions=[
                Position(
                    symbol=Symbol(ticker="AAPL"),
                    quantity=Decimal("100"),
                    market_value=Decimal("50000"),
                    current_price=Decimal("500"),
                )
            ],
            net_assets=Decimal("100000"),
            market_value=Decimal("100000"),
        )
        targets = [TargetAllocation(ticker="AAPL", weight=0.50)]
        # With 0 tolerance, even perfect match should still show
        actions = calculate_rebalance(portfolio, targets, tolerance=0.0)
        assert actions[0].status == "ON_TARGET"  # deviation is 0

    def test_all_positions_on_target(self):
        """Test when all positions are within tolerance."""
        portfolio = Portfolio(
            positions=[
                Position(
                    symbol=Symbol(ticker="AAPL"),
                    quantity=Decimal("50"),
                    market_value=Decimal("50000"),
                    current_price=Decimal("1000"),
                ),
                Position(
                    symbol=Symbol(ticker="GOOGL"),
                    quantity=Decimal("50"),
                    market_value=Decimal("50000"),
                    current_price=Decimal("1000"),
                ),
            ],
            net_assets=Decimal("100000"),
            market_value=Decimal("100000"),
        )
        targets = [
            TargetAllocation(ticker="AAPL", weight=0.50),
            TargetAllocation(ticker="GOOGL", weight=0.50),
        ]
        actions = calculate_rebalance(portfolio, targets, tolerance=0.05)
        assert all(a.status == "ON_TARGET" for a in actions)

    def test_dca_negative_amount(self):
        """Test DCA with negative amount."""
        portfolio = Portfolio(
            positions=[
                Position(
                    symbol=Symbol(ticker="AAPL"),
                    quantity=Decimal("10"),
                    market_value=Decimal("1000"),
                    current_price=Decimal("100"),
                )
            ],
            net_assets=Decimal("1000"),
            market_value=Decimal("1000"),
        )
        targets = [TargetAllocation(ticker="AAPL", weight=0.5)]
        actions = propose_dca_allocation(portfolio, targets, amount=-100)
        assert actions == []

    def test_dca_all_overweight(self):
        """Test DCA when all targets are overweight (nothing to buy)."""
        portfolio = Portfolio(
            positions=[
                Position(
                    symbol=Symbol(ticker="AAPL"),
                    quantity=Decimal("100"),
                    market_value=Decimal("100000"),
                    current_price=Decimal("1000"),
                )
            ],
            net_assets=Decimal("100000"),
            market_value=Decimal("100000"),
        )
        # Target 10% but currently 100%
        targets = [TargetAllocation(ticker="AAPL", weight=0.10)]
        actions = propose_dca_allocation(portfolio, targets, amount=5000)
        assert actions == []

    def test_many_targets(self):
        """Test with many target allocations."""
        portfolio = Portfolio(
            positions=[
                Position(
                    symbol=Symbol(ticker=f"T{i}"),
                    quantity=Decimal("10"),
                    market_value=Decimal("1000"),
                    current_price=Decimal("100"),
                )
                for i in range(20)
            ],
            net_assets=Decimal("20000"),
            market_value=Decimal("20000"),
        )
        targets = [
            TargetAllocation(ticker=f"T{i}", weight=0.05) for i in range(20)
        ]
        actions = calculate_rebalance(portfolio, targets)
        assert len(actions) == 20
