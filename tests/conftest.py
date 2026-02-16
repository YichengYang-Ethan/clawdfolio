"""Shared test fixtures for clawdfolio."""

from decimal import Decimal

import pytest

from clawdfolio.core.types import Exchange, Portfolio, Position, Quote, Symbol


@pytest.fixture
def sample_symbol():
    return Symbol(ticker="AAPL", exchange=Exchange.NASDAQ, name="Apple Inc.")


@pytest.fixture
def sample_quote(sample_symbol):
    return Quote(
        symbol=sample_symbol,
        price=Decimal("175.50"),
        prev_close=Decimal("173.00"),
    )


@pytest.fixture
def sample_position(sample_symbol):
    return Position(
        symbol=sample_symbol,
        quantity=Decimal("100"),
        avg_cost=Decimal("150.00"),
        market_value=Decimal("17550.00"),
        current_price=Decimal("175.50"),
    )


@pytest.fixture
def sample_portfolio(sample_position):
    return Portfolio(
        positions=[sample_position],
        net_assets=Decimal("50000"),
        market_value=Decimal("17550"),
    )
