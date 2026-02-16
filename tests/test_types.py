"""Tests for core data types."""

from decimal import Decimal

from clawdfolio.core.types import (
    AlertSeverity,
    AlertType,
    Exchange,
    Symbol,
    Quote,
    Position,
    Portfolio,
    Alert,
)


class TestSymbol:
    def test_basic_creation(self):
        s = Symbol(ticker="AAPL")
        assert s.ticker == "AAPL"
        assert s.exchange == Exchange.UNKNOWN

    def test_from_dotted_ticker(self):
        s = Symbol(ticker="AAPL.US")
        assert s.ticker == "AAPL"
        assert s.exchange == Exchange.NYSE

    def test_hk_exchange(self):
        s = Symbol(ticker="0700.HK")
        assert s.ticker == "0700"
        assert s.exchange == Exchange.HKEX

    def test_full_symbol(self):
        s = Symbol(ticker="AAPL", exchange=Exchange.NASDAQ)
        assert s.full_symbol == "AAPL.US"

    def test_str(self):
        s = Symbol(ticker="AAPL")
        assert str(s) == "AAPL"

    def test_hash_equality(self):
        s1 = Symbol(ticker="AAPL", exchange=Exchange.NASDAQ)
        s2 = Symbol(ticker="AAPL", exchange=Exchange.NASDAQ)
        assert hash(s1) == hash(s2)


class TestExchange:
    def test_from_suffix(self):
        assert Exchange.from_suffix("US") == Exchange.NYSE
        assert Exchange.from_suffix("HK") == Exchange.HKEX
        assert Exchange.from_suffix("SH") == Exchange.SSE
        assert Exchange.from_suffix("SZ") == Exchange.SZSE
        assert Exchange.from_suffix("XX") == Exchange.UNKNOWN


class TestQuote:
    def test_change(self, sample_quote):
        assert sample_quote.change == Decimal("2.30")

    def test_change_pct(self, sample_quote):
        pct = sample_quote.change_pct
        assert pct is not None
        assert abs(pct - 0.01255) < 0.001

    def test_change_no_prev_close(self, sample_symbol):
        q = Quote(symbol=sample_symbol, price=Decimal("100"))
        assert q.change is None
        assert q.change_pct is None


class TestPosition:
    def test_update_from_quote(self, sample_position, sample_quote):
        sample_position.update_from_quote(sample_quote)
        assert sample_position.current_price == Decimal("185.50")
        assert sample_position.market_value == Decimal("18550.00")

    def test_unrealized_pnl(self, sample_position, sample_quote):
        sample_position.update_from_quote(sample_quote)
        expected_pnl = Decimal("100") * (Decimal("185.50") - Decimal("150.00"))
        assert sample_position.unrealized_pnl == expected_pnl


class TestPortfolio:
    def test_weights_updated(self, sample_portfolio):
        pos = sample_portfolio.positions[0]
        assert pos.weight > 0

    def test_get_position(self, sample_portfolio):
        pos = sample_portfolio.get_position("AAPL")
        assert pos is not None
        assert pos.symbol.ticker == "AAPL"

    def test_get_position_not_found(self, sample_portfolio):
        assert sample_portfolio.get_position("MSFT") is None

    def test_sorted_by_weight(self, sample_portfolio):
        sorted_pos = sample_portfolio.sorted_by_weight
        assert len(sorted_pos) == 1

    def test_top_holdings(self, sample_portfolio):
        top = sample_portfolio.top_holdings
        assert len(top) <= 10


class TestAlert:
    def test_alert_str(self):
        alert = Alert(
            type=AlertType.PRICE_MOVE,
            severity=AlertSeverity.WARNING,
            title="Big Move",
            message="AAPL moved 5%",
        )
        result = str(alert)
        assert "Big Move" in result
        assert "AAPL moved 5%" in result
