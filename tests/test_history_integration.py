"""Integration tests for portfolio history snapshot round-trip."""

from datetime import datetime
from decimal import Decimal

import pytest

from clawdfolio.core.types import Portfolio, Position, Symbol
from clawdfolio.storage.database import get_connection, init_db
from clawdfolio.storage.repository import get_performance, get_snapshots, save_snapshot


@pytest.fixture
def db_path(tmp_path):
    """Create a temp database."""
    path = str(tmp_path / "integration.db")
    init_db(path)
    return path


@pytest.fixture
def portfolio():
    """Build a realistic portfolio."""
    positions = [
        Position(
            symbol=Symbol(ticker="TQQQ"),
            quantity=Decimal("500"),
            avg_cost=Decimal("40"),
            market_value=Decimal("35000"),
            current_price=Decimal("70"),
            day_pnl=Decimal("1500"),
            day_pnl_pct=0.045,
        ),
        Position(
            symbol=Symbol(ticker="QQQ"),
            quantity=Decimal("200"),
            avg_cost=Decimal("350"),
            market_value=Decimal("80000"),
            current_price=Decimal("400"),
            day_pnl=Decimal("-500"),
            day_pnl_pct=-0.006,
        ),
        Position(
            symbol=Symbol(ticker="SPY"),
            quantity=Decimal("100"),
            avg_cost=Decimal("420"),
            market_value=Decimal("45000"),
            current_price=Decimal("450"),
            day_pnl=Decimal("200"),
            day_pnl_pct=0.004,
        ),
    ]
    return Portfolio(
        positions=positions,
        cash=Decimal("10000"),
        net_assets=Decimal("170000"),
        market_value=Decimal("160000"),
        day_pnl=Decimal("1200"),
        day_pnl_pct=0.007,
        source="integration_test",
    )


class TestSnapshotRoundTrip:
    """End-to-end snapshot save and retrieve tests."""

    def test_save_and_retrieve_snapshot(self, db_path, portfolio):
        """Test full round-trip: save -> retrieve -> verify."""
        saved = save_snapshot(portfolio, db_path=db_path)

        assert saved.id is not None
        assert saved.net_assets == 170000.0
        assert saved.cash == 10000.0
        assert saved.day_pnl == 1200.0
        assert len(saved.positions) == 3

        retrieved = get_snapshots(days=1, db_path=db_path)
        assert len(retrieved) == 1
        assert retrieved[0].net_assets == saved.net_assets

    def test_position_data_persisted(self, db_path, portfolio):
        """Test that position data is correctly persisted."""
        saved = save_snapshot(portfolio, db_path=db_path)

        conn = get_connection(db_path)
        rows = conn.execute(
            "SELECT ticker, quantity, avg_cost, market_value, weight "
            "FROM position_snapshots WHERE snapshot_id = ?",
            (saved.id,),
        ).fetchall()
        conn.close()

        tickers = {row["ticker"] for row in rows}
        assert tickers == {"TQQQ", "QQQ", "SPY"}

    def test_multiple_days_snapshots(self, db_path, portfolio):
        """Test saving snapshots across multiple calls."""
        for _ in range(5):
            save_snapshot(portfolio, db_path=db_path)

        snapshots = get_snapshots(days=1, db_path=db_path)
        assert len(snapshots) == 5

    def test_performance_from_snapshots(self, db_path, portfolio):
        """Test performance calculation from real snapshots."""
        save_snapshot(portfolio, db_path=db_path)
        save_snapshot(portfolio, db_path=db_path)

        metrics = get_performance(days=1, db_path=db_path)
        assert metrics is not None
        assert metrics.total_snapshots == 2
        assert metrics.starting_nav == 170000.0
        assert metrics.ending_nav == 170000.0

    def test_performance_with_varying_nav(self, db_path):
        """Test performance with changing NAV values."""
        conn = get_connection(db_path)
        navs = [100000, 102000, 99000, 103000, 105000]
        for nav in navs:
            conn.execute(
                "INSERT INTO portfolio_snapshots "
                "(timestamp, net_assets, cash, market_value, day_pnl, source) "
                "VALUES (?, ?, 0, ?, 0, 'test')",
                (datetime.now().isoformat(), nav, nav),
            )
        conn.commit()
        conn.close()

        metrics = get_performance(days=1, db_path=db_path)
        assert metrics is not None
        assert metrics.total_return_pct == pytest.approx(0.05, abs=0.001)
        assert metrics.starting_nav == 100000
        assert metrics.ending_nav == 105000
