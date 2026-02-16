"""Shared test fixtures for clawdfolio."""

import pytest

from clawdfolio.core.types import Exchange, Symbol, Position, Quote, Portfolio
from decimal import Decimal


@pytest.fixture
def sample_symbol():
    return Symbol(ticker="AAPL", exchange=Exchange.NASDAQ, name="Apple Inc.")


@pytest.fixture
def sample_quote(sample_symbol):
    return Quote(
        symbol=sample_symbol,
        price=Decimal("185.50"),
        prev_close=Decimal("183.20"),
    )


@pytest.fixture
def sample_position(sample_symbol):
    return Position(
        symbol=sample_symbol,
        quantity=Decimal("100"),
        avg_cost=Decimal("150.00"),
        market_value=Decimal("18550.00"),
        current_price=Decimal("185.50"),
    )


@pytest.fixture
def sample_portfolio(sample_position):
    return Portfolio(
        positions=[sample_position],
        net_assets=Decimal("50000"),
        market_value=Decimal("18550"),
    )
