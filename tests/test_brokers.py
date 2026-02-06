"""Tests for broker integrations."""


import pytest

from portfolio_monitor.brokers.base import BaseBroker
from portfolio_monitor.brokers.demo import DemoBroker
from portfolio_monitor.brokers.registry import (
    get_broker,
    list_brokers,
    register_broker,
    unregister_broker,
)
from portfolio_monitor.core.types import Exchange, Symbol


class TestBrokerRegistry:
    """Tests for broker registry."""

    def test_register_broker(self):
        """Test registering a new broker."""
        @register_broker("test_broker")
        class TestBroker(BaseBroker):
            def connect(self):
                return True

            def disconnect(self):
                pass

            def is_connected(self):
                return True

            def get_portfolio(self):
                pass

            def get_positions(self):
                return []

            def get_quote(self, symbol):
                pass

            def get_quotes(self, symbols):
                return {}

        assert "test_broker" in list_brokers()
        unregister_broker("test_broker")

    def test_get_broker(self):
        """Test getting a registered broker."""
        # Register demo broker first
        from portfolio_monitor.brokers.demo import DemoBroker  # noqa

        broker = get_broker("demo")
        assert isinstance(broker, DemoBroker)

    def test_get_unknown_broker(self):
        """Test getting unknown broker raises error."""
        with pytest.raises(KeyError):
            get_broker("nonexistent")

    def test_register_duplicate_broker(self):
        """Test registering duplicate broker raises error."""
        @register_broker("duplicate_test")
        class TestBroker1(BaseBroker):
            def connect(self): return True
            def disconnect(self): pass
            def is_connected(self): return True
            def get_portfolio(self): pass
            def get_positions(self): return []
            def get_quote(self, s): pass
            def get_quotes(self, s): return {}

        with pytest.raises(ValueError):
            @register_broker("duplicate_test")
            class TestBroker2(BaseBroker):
                def connect(self): return True
                def disconnect(self): pass
                def is_connected(self): return True
                def get_portfolio(self): pass
                def get_positions(self): return []
                def get_quote(self, s): pass
                def get_quotes(self, s): return {}

        unregister_broker("duplicate_test")


class TestDemoBroker:
    """Tests for demo broker."""

    def test_demo_broker_connect(self):
        """Test demo broker connection."""

        broker = DemoBroker()
        assert broker.connect() is True
        assert broker.is_connected() is True

    def test_demo_broker_disconnect(self):
        """Test demo broker disconnection."""

        broker = DemoBroker()
        broker.connect()
        broker.disconnect()
        assert broker.is_connected() is False

    def test_demo_broker_get_portfolio(self):
        """Test demo broker portfolio."""

        broker = DemoBroker()
        broker.connect()
        portfolio = broker.get_portfolio()

        assert portfolio is not None
        assert portfolio.net_assets > 0
        assert len(portfolio.positions) > 0
        assert portfolio.source == "demo"

    def test_demo_broker_get_positions(self):
        """Test demo broker positions."""

        broker = DemoBroker()
        broker.connect()
        positions = broker.get_positions()

        assert len(positions) > 0
        for pos in positions:
            assert pos.quantity > 0
            assert pos.market_value > 0

    def test_demo_broker_get_quote(self):
        """Test demo broker quote."""

        broker = DemoBroker()
        broker.connect()

        symbol = Symbol(ticker="AAPL", exchange=Exchange.NYSE)
        quote = broker.get_quote(symbol)

        assert quote is not None
        assert quote.price > 0
        assert quote.source == "demo"

    def test_demo_broker_get_quotes(self):
        """Test demo broker multiple quotes."""

        broker = DemoBroker()
        broker.connect()

        symbols = [
            Symbol(ticker="AAPL"),
            Symbol(ticker="MSFT"),
            Symbol(ticker="GOOGL"),
        ]
        quotes = broker.get_quotes(symbols)

        assert len(quotes) == 3
        assert "AAPL" in quotes
        assert "MSFT" in quotes

    def test_demo_broker_context_manager(self):
        """Test demo broker as context manager."""

        with DemoBroker() as broker:
            assert broker.is_connected()
            portfolio = broker.get_portfolio()
            assert portfolio is not None

    def test_demo_broker_add_position(self):
        """Test adding custom position to demo broker."""

        broker = DemoBroker()
        broker.connect()

        initial_count = len(broker.get_positions())
        broker.add_demo_position("TEST", "Test Stock", 100, 50.0, 45.0)

        assert len(broker.get_positions()) == initial_count + 1

    def test_demo_broker_reset(self):
        """Test resetting demo broker."""

        broker = DemoBroker()
        broker.connect()

        broker.add_demo_position("TEST", "Test Stock", 100, 50.0, 45.0)
        broker.reset()

        # Should be back to default positions
        positions = broker.get_positions()
        tickers = [p.symbol.ticker for p in positions]
        assert "TEST" not in tickers
