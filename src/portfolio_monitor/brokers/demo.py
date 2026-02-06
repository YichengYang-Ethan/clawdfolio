"""Demo broker for testing without real credentials."""

from __future__ import annotations

import random
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from ..core.types import Exchange, Portfolio, Position, Quote, Symbol
from .base import BaseBroker
from .registry import register_broker

if TYPE_CHECKING:
    from ..core.config import BrokerConfig

# Sample demo data
DEMO_POSITIONS = [
    ("AAPL", "Apple Inc.", 50, 175.50, 168.00),
    ("MSFT", "Microsoft Corp.", 30, 380.25, 370.00),
    ("GOOGL", "Alphabet Inc.", 10, 140.80, 135.00),
    ("NVDA", "NVIDIA Corp.", 25, 480.00, 420.00),
    ("TSLA", "Tesla Inc.", 15, 248.50, 260.00),
    ("AMZN", "Amazon.com Inc.", 20, 178.90, 172.00),
    ("META", "Meta Platforms", 12, 505.30, 490.00),
    ("TQQQ", "ProShares UltraPro QQQ", 100, 62.50, 58.00),
    ("SPY", "SPDR S&P 500 ETF", 40, 520.00, 515.00),
    ("QQQ", "Invesco QQQ Trust", 25, 440.50, 435.00),
]


@register_broker("demo")
class DemoBroker(BaseBroker):
    """Demo broker with simulated portfolio data.

    Useful for:
    - Testing without real API credentials
    - Development and debugging
    - Demonstrating functionality
    """

    name = "demo"
    display_name = "Demo Broker"

    def __init__(self, config: BrokerConfig | None = None):
        super().__init__(config)
        self._connected = False
        self._positions: list[tuple] = DEMO_POSITIONS.copy()

    def connect(self) -> bool:
        """Simulate connection."""
        self._connected = True
        return True

    def disconnect(self) -> None:
        """Simulate disconnection."""
        self._connected = False

    def is_connected(self) -> bool:
        """Check connection status."""
        return self._connected

    def get_portfolio(self) -> Portfolio:
        """Generate demo portfolio."""
        positions = self.get_positions()

        total_mv = sum((p.market_value for p in positions), Decimal(0))
        total_day_pnl = sum((p.day_pnl for p in positions), Decimal(0))
        cash = Decimal("15000.00")
        net_assets = total_mv + cash

        portfolio = Portfolio(
            positions=positions,
            cash=cash,
            net_assets=net_assets,
            market_value=total_mv,
            buying_power=cash * Decimal("2"),  # Simulate margin
            day_pnl=total_day_pnl,
            day_pnl_pct=float(total_day_pnl / net_assets) if net_assets > 0 else 0.0,
            currency="USD",
            source="demo",
            timestamp=datetime.now(),
        )

        return portfolio

    def get_positions(self) -> list[Position]:
        """Generate demo positions."""
        positions = []

        for ticker, name, qty, price, avg_cost in self._positions:
            # Add some random price movement
            price_var = Decimal(str(random.uniform(-0.02, 0.02)))
            current_price = Decimal(str(price)) * (1 + price_var)
            prev_close = Decimal(str(price)) * Decimal("0.995")

            symbol = Symbol(ticker=ticker, exchange=Exchange.NYSE, name=name)
            quantity = Decimal(str(qty))
            avg_cost_dec = Decimal(str(avg_cost))

            market_value = quantity * current_price
            unrealized_pnl = quantity * (current_price - avg_cost_dec)
            day_pnl = quantity * (current_price - prev_close)

            positions.append(
                Position(
                    symbol=symbol,
                    quantity=quantity,
                    avg_cost=avg_cost_dec,
                    market_value=market_value,
                    unrealized_pnl=unrealized_pnl,
                    unrealized_pnl_pct=float(
                        (current_price - avg_cost_dec) / avg_cost_dec
                    ),
                    day_pnl=day_pnl,
                    day_pnl_pct=float((current_price - prev_close) / prev_close),
                    current_price=current_price,
                    prev_close=prev_close,
                    name=name,
                    source="demo",
                )
            )

        return positions

    def get_quote(self, symbol: Symbol) -> Quote:
        """Generate demo quote for a symbol."""
        # Find in demo positions or generate random
        for ticker, _name, _, base_price, _ in self._positions:
            if ticker == symbol.ticker:
                price_var = Decimal(str(random.uniform(-0.02, 0.02)))
                price = Decimal(str(base_price)) * (1 + price_var)
                prev_close = Decimal(str(base_price)) * Decimal("0.995")

                return Quote(
                    symbol=symbol,
                    price=price,
                    prev_close=prev_close,
                    open=prev_close * Decimal("1.001"),
                    high=price * Decimal("1.01"),
                    low=price * Decimal("0.99"),
                    volume=random.randint(1000000, 50000000),
                    timestamp=datetime.now(),
                    source="demo",
                )

        # Generate random quote for unknown symbol
        base_price = Decimal(str(random.uniform(50, 500)))
        return Quote(
            symbol=symbol,
            price=base_price,
            prev_close=base_price * Decimal("0.995"),
            volume=random.randint(100000, 10000000),
            timestamp=datetime.now(),
            source="demo",
        )

    def get_quotes(self, symbols: list[Symbol]) -> dict[str, Quote]:
        """Generate demo quotes for multiple symbols."""
        return {s.ticker: self.get_quote(s) for s in symbols}

    def add_demo_position(
        self, ticker: str, name: str, qty: int, price: float, avg_cost: float
    ) -> None:
        """Add a custom position to demo portfolio."""
        self._positions.append((ticker, name, qty, price, avg_cost))

    def clear_positions(self) -> None:
        """Clear all demo positions."""
        self._positions = []

    def reset(self) -> None:
        """Reset to default demo positions."""
        self._positions = DEMO_POSITIONS.copy()
