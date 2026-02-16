"""Tests for portfolio data export."""

import csv
import io
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
from clawdfolio.output.export import (
    export_alerts_csv,
    export_alerts_json,
    export_portfolio_csv,
    export_portfolio_json,
    export_risk_csv,
    export_risk_json,
)


def _make_portfolio():
    pos = Position(
        symbol=Symbol(ticker="AAPL", exchange=Exchange.NASDAQ, name="Apple"),
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
    )


def _make_risk_metrics():
    return RiskMetrics(
        volatility_20d=0.25,
        volatility_60d=0.22,
        beta_spy=1.2,
        sharpe_ratio=1.5,
        var_95=0.03,
        var_99=0.05,
        max_drawdown=0.15,
        current_drawdown=0.05,
        rsi_portfolio=55.0,
        timestamp=datetime(2026, 1, 15),
    )


def _make_alerts():
    return [
        Alert(
            type=AlertType.PRICE_MOVE,
            severity=AlertSeverity.WARNING,
            title="AAPL up 5.2%",
            message="AAPL moved significantly",
            ticker="AAPL",
            value=0.052,
            threshold=0.05,
        ),
    ]


class TestExportPortfolioCSV:
    def test_basic_export(self):
        csv_str = export_portfolio_csv(_make_portfolio())
        reader = csv.reader(io.StringIO(csv_str))
        rows = list(reader)
        assert rows[0][0] == "ticker"  # Header
        assert len(rows) == 2  # Header + 1 position
        assert rows[1][0] == "AAPL"

    def test_csv_has_all_columns(self):
        csv_str = export_portfolio_csv(_make_portfolio())
        reader = csv.reader(io.StringIO(csv_str))
        header = next(reader)
        assert "ticker" in header
        assert "weight" in header
        assert "market_value" in header
        assert "unrealized_pnl" in header


class TestExportRiskCSV:
    def test_basic_export(self):
        csv_str = export_risk_csv(_make_risk_metrics())
        reader = csv.reader(io.StringIO(csv_str))
        rows = list(reader)
        assert rows[0] == ["metric", "value"]
        # Find volatility_20d row
        vol_row = [r for r in rows if r[0] == "volatility_20d"]
        assert len(vol_row) == 1
        assert float(vol_row[0][1]) == pytest.approx(0.25, rel=1e-3)


class TestExportAlertsCSV:
    def test_basic_export(self):
        csv_str = export_alerts_csv(_make_alerts())
        reader = csv.reader(io.StringIO(csv_str))
        rows = list(reader)
        assert len(rows) == 2  # Header + 1 alert
        assert rows[1][0] == "price_move"

    def test_empty_alerts(self):
        csv_str = export_alerts_csv([])
        reader = csv.reader(io.StringIO(csv_str))
        rows = list(reader)
        assert len(rows) == 1  # Just header


class TestExportJSON:
    def test_portfolio_json(self):
        result = export_portfolio_json(_make_portfolio())
        parsed = json.loads(result)
        assert "summary" in parsed
        assert "positions" in parsed

    def test_risk_json(self):
        result = export_risk_json(_make_risk_metrics())
        parsed = json.loads(result)
        assert "volatility" in parsed

    def test_alerts_json(self):
        result = export_alerts_json(_make_alerts())
        parsed = json.loads(result)
        assert parsed["count"] == 1
