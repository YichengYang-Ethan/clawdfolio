"""Tests for JSON output formatting."""

import json
from datetime import datetime
from decimal import Decimal

import pytest

from clawdfolio.core.types import (
    Alert,
    AlertSeverity,
    AlertType,
    Exchange,
    Portfolio,
    Position,
    RiskMetrics,
    Symbol,
)
from clawdfolio.output.json import CustomJSONEncoder, JSONFormatter, to_json


class TestCustomJSONEncoder:
    def test_decimal(self):
        result = json.dumps({"val": Decimal("3.14")}, cls=CustomJSONEncoder)
        assert "3.14" in result

    def test_datetime(self):
        dt = datetime(2026, 1, 15, 10, 30, 0)
        result = json.dumps({"ts": dt}, cls=CustomJSONEncoder)
        assert "2026-01-15" in result

    def test_enum(self):
        result = json.dumps({"ex": Exchange.NYSE}, cls=CustomJSONEncoder)
        assert "NYSE" in result

    def test_dataclass(self):
        sym = Symbol(ticker="AAPL", exchange=Exchange.NASDAQ)
        result = json.dumps({"sym": sym}, cls=CustomJSONEncoder)
        parsed = json.loads(result)
        assert parsed["sym"]["ticker"] == "AAPL"

    def test_unsupported_type_raises(self):
        with pytest.raises(TypeError):
            json.dumps({"val": object()}, cls=CustomJSONEncoder)


class TestJSONFormatter:
    def _make_portfolio(self):
        pos = Position(
            symbol=Symbol(ticker="AAPL", exchange=Exchange.NASDAQ),
            quantity=Decimal("100"),
            avg_cost=Decimal("150.00"),
            market_value=Decimal("17500"),
            current_price=Decimal("175.00"),
            day_pnl=Decimal("200"),
            day_pnl_pct=0.012,
            unrealized_pnl=Decimal("2500"),
            unrealized_pnl_pct=0.167,
        )
        return Portfolio(
            positions=[pos],
            net_assets=Decimal("50000"),
            market_value=Decimal("17500"),
            day_pnl=Decimal("200"),
            day_pnl_pct=0.012,
        )

    def test_format_portfolio(self):
        portfolio = self._make_portfolio()
        formatter = JSONFormatter()
        result = formatter.format_portfolio(portfolio)
        parsed = json.loads(result)
        assert "summary" in parsed
        assert "positions" in parsed
        assert parsed["summary"]["net_assets"] == 50000.0
        assert len(parsed["positions"]) == 1
        assert parsed["positions"][0]["ticker"] == "AAPL"

    def test_format_risk_metrics(self):
        metrics = RiskMetrics(
            volatility_20d=0.25,
            beta_spy=1.2,
            sharpe_ratio=1.5,
            var_95=0.03,
            max_drawdown=0.15,
            timestamp=datetime(2026, 1, 15),
        )
        formatter = JSONFormatter()
        result = formatter.format_risk_metrics(metrics)
        parsed = json.loads(result)
        assert parsed["volatility"]["20d"] == 0.25
        assert parsed["beta"]["spy"] == 1.2
        assert parsed["sharpe_ratio"] == 1.5

    def test_format_alerts(self):
        alert = Alert(
            type=AlertType.PRICE_MOVE,
            severity=AlertSeverity.WARNING,
            title="AAPL up 5.2%",
            message="AAPL moved significantly",
            ticker="AAPL",
            value=0.052,
            threshold=0.05,
        )
        formatter = JSONFormatter()
        result = formatter.format_alerts([alert])
        parsed = json.loads(result)
        assert parsed["count"] == 1
        assert parsed["alerts"][0]["type"] == "price_move"
        assert parsed["alerts"][0]["severity"] == "warning"

    def test_format_empty_alerts(self):
        formatter = JSONFormatter()
        result = formatter.format_alerts([])
        parsed = json.loads(result)
        assert parsed["count"] == 0
        assert parsed["alerts"] == []


class TestToJson:
    def test_simple_dict(self):
        result = to_json({"key": "value"})
        parsed = json.loads(result)
        assert parsed["key"] == "value"

    def test_nested_with_decimal(self):
        result = to_json({"price": Decimal("99.99"), "items": [1, 2, 3]})
        parsed = json.loads(result)
        assert parsed["price"] == 99.99

    def test_custom_indent(self):
        result = to_json({"a": 1}, indent=4)
        assert "    " in result  # 4-space indent
