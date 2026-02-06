"""Pytest configuration and fixtures."""

from decimal import Decimal

import pytest

from portfolio_monitor.brokers.registry import clear_registry
from portfolio_monitor.core.types import (
    Exchange,
    Portfolio,
    Position,
    Quote,
    Symbol,
)


@pytest.fixture
def sample_symbol():
    """Create a sample symbol."""
    return Symbol(ticker="AAPL", exchange=Exchange.NYSE, name="Apple Inc.")


@pytest.fixture
def sample_quote(sample_symbol):
    """Create a sample quote."""
    return Quote(
        symbol=sample_symbol,
        price=Decimal("175.50"),
        prev_close=Decimal("173.00"),
        volume=50000000,
        source="test",
    )


@pytest.fixture
def sample_position(sample_symbol):
    """Create a sample position."""
    return Position(
        symbol=sample_symbol,
        quantity=Decimal("100"),
        avg_cost=Decimal("150.00"),
        market_value=Decimal("17550.00"),
        unrealized_pnl=Decimal("2550.00"),
        unrealized_pnl_pct=0.17,
        day_pnl=Decimal("250.00"),
        day_pnl_pct=0.0144,
        current_price=Decimal("175.50"),
        prev_close=Decimal("173.00"),
        name="Apple Inc.",
        source="test",
    )


@pytest.fixture
def sample_portfolio():
    """Create a sample portfolio with multiple positions."""
    positions = [
        Position(
            symbol=Symbol(ticker="AAPL", exchange=Exchange.NYSE),
            quantity=Decimal("100"),
            avg_cost=Decimal("150.00"),
            market_value=Decimal("17550.00"),
            day_pnl=Decimal("250.00"),
            day_pnl_pct=0.0144,
            current_price=Decimal("175.50"),
            source="test",
        ),
        Position(
            symbol=Symbol(ticker="MSFT", exchange=Exchange.NYSE),
            quantity=Decimal("50"),
            avg_cost=Decimal("350.00"),
            market_value=Decimal("19000.00"),
            day_pnl=Decimal("-100.00"),
            day_pnl_pct=-0.0052,
            current_price=Decimal("380.00"),
            source="test",
        ),
        Position(
            symbol=Symbol(ticker="GOOGL", exchange=Exchange.NYSE),
            quantity=Decimal("30"),
            avg_cost=Decimal("130.00"),
            market_value=Decimal("4200.00"),
            day_pnl=Decimal("60.00"),
            day_pnl_pct=0.0145,
            current_price=Decimal("140.00"),
            source="test",
        ),
    ]

    return Portfolio(
        positions=positions,
        cash=Decimal("10000.00"),
        net_assets=Decimal("50750.00"),
        market_value=Decimal("40750.00"),
        buying_power=Decimal("20000.00"),
        day_pnl=Decimal("210.00"),
        day_pnl_pct=0.0041,
        currency="USD",
        source="test",
    )


@pytest.fixture
def clean_registry():
    """Provide a clean broker registry for tests that need isolation.

    Not autouse - only tests that explicitly request it will get a clean registry.
    """
    clear_registry()
    yield
    clear_registry()


@pytest.fixture
def demo_broker():
    """Provide a demo broker instance."""
    # Import to ensure registration
    from portfolio_monitor.brokers import get_broker

    broker = get_broker("demo")
    broker.connect()
    yield broker
    broker.disconnect()
