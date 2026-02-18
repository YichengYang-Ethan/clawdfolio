"""Tests for history/snapshot module."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from clawdfolio.core.history import (
    SnapshotRow,
    append_snapshot,
    compute_performance,
    filter_by_period,
    format_performance_table,
    read_snapshots,
)
from clawdfolio.core.types import Exchange, Portfolio, Position, Symbol


def _make_portfolio(**overrides) -> Portfolio:
    """Create a minimal portfolio for testing."""
    defaults = {
        "positions": [
            Position(
                symbol=Symbol(ticker="AAPL", exchange=Exchange.NASDAQ),
                quantity=Decimal("10"),
                market_value=Decimal("1750"),
                current_price=Decimal("175"),
            )
        ],
        "net_assets": Decimal("10000"),
        "market_value": Decimal("1750"),
        "cash": Decimal("8250"),
        "day_pnl": Decimal("50"),
        "day_pnl_pct": 0.005,
    }
    defaults.update(overrides)
    return Portfolio(**defaults)


class TestAppendAndReadSnapshots:
    """Tests for append_snapshot and read_snapshots."""

    def test_write_and_read(self, tmp_path):
        path = str(tmp_path / "history.csv")
        portfolio = _make_portfolio()

        written, msg = append_snapshot(portfolio, path)
        assert written is True
        assert "Snapshot saved" in msg

        rows = read_snapshots(path)
        assert len(rows) == 1
        assert rows[0].net_assets == 10000.0
        assert rows[0].market_value == 1750.0
        assert rows[0].cash == 8250.0

    def test_idempotent_same_day(self, tmp_path):
        path = str(tmp_path / "history.csv")
        portfolio = _make_portfolio()

        append_snapshot(portfolio, path)
        written, msg = append_snapshot(portfolio, path)
        assert written is False
        assert "already exists" in msg

        rows = read_snapshots(path)
        assert len(rows) == 1

    def test_creates_parent_dirs(self, tmp_path):
        path = str(tmp_path / "sub" / "dir" / "history.csv")
        portfolio = _make_portfolio()

        written, _ = append_snapshot(portfolio, path)
        assert written is True

    def test_read_nonexistent_file(self, tmp_path):
        rows = read_snapshots(str(tmp_path / "nope.csv"))
        assert rows == []

    def test_read_malformed_rows_skipped(self, tmp_path):
        path = tmp_path / "history.csv"
        path.write_text(
            "date,net_assets,market_value,cash,day_pnl,day_pnl_pct\n"
            "2025-01-01,10000,5000,5000,100,0.01\n"
            "bad-date,x,y,z,a,b\n"
            "2025-01-02,11000,6000,5000,200,0.02\n"
        )
        rows = read_snapshots(str(path))
        assert len(rows) == 2


class TestFilterByPeriod:
    """Tests for filter_by_period."""

    def _make_rows(self, days_ago_list: list[int]) -> list[SnapshotRow]:
        today = date.today()
        return [
            SnapshotRow(
                date=today - timedelta(days=d),
                net_assets=10000 + d,
                market_value=5000,
                cash=5000,
                day_pnl=0,
                day_pnl_pct=0,
            )
            for d in days_ago_list
        ]

    def test_filter_all(self):
        rows = self._make_rows([0, 50, 100, 200, 400])
        assert filter_by_period(rows, "all") == rows

    def test_filter_1m(self):
        rows = self._make_rows([0, 15, 29, 31, 60])
        result = filter_by_period(rows, "1m")
        assert len(result) == 3

    def test_filter_3m(self):
        rows = self._make_rows([0, 45, 89, 92, 200])
        result = filter_by_period(rows, "3m")
        assert len(result) == 3  # 0, 45, 89 are within 91 days

    def test_filter_unknown_period(self):
        rows = self._make_rows([0, 10])
        assert filter_by_period(rows, "2w") == rows

    def test_filter_empty(self):
        assert filter_by_period([], "1m") == []


class TestComputePerformance:
    """Tests for compute_performance."""

    def test_empty_rows(self):
        result = compute_performance([])
        assert "error" in result

    def test_basic_performance(self):
        rows = [
            SnapshotRow(
                date=date(2025, 1, 1),
                net_assets=10000,
                market_value=5000,
                cash=5000,
                day_pnl=0,
                day_pnl_pct=0.0,
            ),
            SnapshotRow(
                date=date(2025, 1, 2),
                net_assets=10100,
                market_value=5100,
                cash=5000,
                day_pnl=100,
                day_pnl_pct=0.01,
            ),
            SnapshotRow(
                date=date(2025, 1, 3),
                net_assets=10200,
                market_value=5200,
                cash=5000,
                day_pnl=100,
                day_pnl_pct=0.0099,
            ),
        ]
        result = compute_performance(rows)
        assert result["total_return_pct"] == 2.0
        assert result["data_points"] == 3
        assert result["start_nav"] == 10000
        assert result["end_nav"] == 10200
        assert result["max_drawdown_pct"] == 0.0  # monotonic increase

    def test_drawdown(self):
        rows = [
            SnapshotRow(
                date=date(2025, 1, 1),
                net_assets=10000,
                market_value=5000,
                cash=5000,
                day_pnl=0,
                day_pnl_pct=0,
            ),
            SnapshotRow(
                date=date(2025, 1, 2),
                net_assets=9000,
                market_value=4000,
                cash=5000,
                day_pnl=-1000,
                day_pnl_pct=-0.1,
            ),
            SnapshotRow(
                date=date(2025, 1, 3),
                net_assets=9500,
                market_value=4500,
                cash=5000,
                day_pnl=500,
                day_pnl_pct=0.0556,
            ),
        ]
        result = compute_performance(rows)
        assert result["max_drawdown_pct"] == -10.0
        assert result["worst_day"]["pnl_pct"] == -10.0

    def test_best_worst_day(self):
        rows = [
            SnapshotRow(
                date=date(2025, 1, 1),
                net_assets=10000,
                market_value=5000,
                cash=5000,
                day_pnl=0,
                day_pnl_pct=0.0,
            ),
            SnapshotRow(
                date=date(2025, 1, 2),
                net_assets=10500,
                market_value=5500,
                cash=5000,
                day_pnl=500,
                day_pnl_pct=0.05,
            ),
            SnapshotRow(
                date=date(2025, 1, 3),
                net_assets=10200,
                market_value=5200,
                cash=5000,
                day_pnl=-300,
                day_pnl_pct=-0.03,
            ),
        ]
        result = compute_performance(rows)
        assert result["best_day"]["date"] == "2025-01-02"
        assert result["worst_day"]["date"] == "2025-01-03"


class TestFormatPerformanceTable:
    """Tests for format_performance_table."""

    def test_format_error(self):
        result = format_performance_table({"error": "No data"})
        assert result == "No data"

    def test_format_normal(self):
        perf = {
            "start_date": "2025-01-01",
            "end_date": "2025-01-03",
            "start_nav": 10000,
            "end_nav": 10200,
            "total_return_pct": 2.0,
            "max_drawdown_pct": -1.0,
            "best_day": {"date": "2025-01-02", "pnl_pct": 1.5},
            "worst_day": {"date": "2025-01-03", "pnl_pct": -0.5},
            "data_points": 3,
        }
        table = format_performance_table(perf)
        assert "Portfolio Performance" in table
        assert "10,000" in table
        assert "+2.00%" in table
