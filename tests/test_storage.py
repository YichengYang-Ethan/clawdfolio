"""Tests for portfolio history storage."""

import sqlite3
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import pytest

from clawdfolio.core.types import Portfolio, Position, Symbol
from clawdfolio.storage.database import get_connection, get_db_path, init_db
from clawdfolio.storage.models import PerformanceMetrics, PortfolioSnapshot, PositionSnapshot
from clawdfolio.storage.repository import get_performance, get_snapshots, save_snapshot


@pytest.fixture
def tmp_db(tmp_path):
    """Return a temporary database path."""
    return str(tmp_path / "test.db")


@pytest.fixture
def sample_portfolio():
    """Create a sample portfolio for testing."""
    positions = [
        Position(
            symbol=Symbol(ticker="AAPL"),
            quantity=Decimal("100"),
            avg_cost=Decimal("150"),
            market_value=Decimal("17000"),
            current_price=Decimal("170"),
            day_pnl=Decimal("200"),
        ),
        Position(
            symbol=Symbol(ticker="GOOGL"),
            quantity=Decimal("50"),
            avg_cost=Decimal("130"),
            market_value=Decimal("7500"),
            current_price=Decimal("150"),
            day_pnl=Decimal("-100"),
        ),
    ]
    return Portfolio(
        positions=positions,
        cash=Decimal("5000"),
        net_assets=Decimal("29500"),
        market_value=Decimal("24500"),
        day_pnl=Decimal("100"),
        source="test",
    )


class TestDatabase:
    """Tests for database module."""

    def test_get_db_path_default(self):
        """Test default database path."""
        path = get_db_path()
        assert path.name == "portfolio_history.db"
        assert ".cache" in str(path)

    def test_get_db_path_custom(self, tmp_path):
        """Test custom database path."""
        custom = str(tmp_path / "custom.db")
        path = get_db_path(custom)
        assert path == Path(custom)

    def test_init_db(self, tmp_db):
        """Test database initialization."""
        path = init_db(tmp_db)
        assert path.exists()

        conn = sqlite3.connect(str(path))
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()

        assert "portfolio_snapshots" in tables
        assert "position_snapshots" in tables
        assert "schema_version" in tables

    def test_get_connection(self, tmp_db):
        """Test getting a database connection."""
        conn = get_connection(tmp_db)
        assert conn is not None
        conn.close()

    def test_schema_idempotent(self, tmp_db):
        """Test that schema creation is idempotent."""
        conn1 = get_connection(tmp_db)
        conn1.close()
        conn2 = get_connection(tmp_db)
        conn2.close()


class TestModels:
    """Tests for data models."""

    def test_portfolio_snapshot_creation(self):
        """Test PortfolioSnapshot creation."""
        snap = PortfolioSnapshot(
            timestamp=datetime.now(),
            net_assets=100000.0,
            cash=5000.0,
            market_value=95000.0,
            day_pnl=500.0,
        )
        assert snap.net_assets == 100000.0
        assert snap.id is None
        assert snap.positions == []

    def test_position_snapshot_creation(self):
        """Test PositionSnapshot creation."""
        pos = PositionSnapshot(
            ticker="AAPL",
            quantity=100,
            avg_cost=150.0,
            market_value=17000.0,
            weight=0.17,
        )
        assert pos.ticker == "AAPL"
        assert pos.weight == 0.17

    def test_performance_metrics(self):
        """Test PerformanceMetrics creation."""
        m = PerformanceMetrics(
            total_snapshots=30,
            first_date=datetime(2024, 1, 1),
            last_date=datetime(2024, 1, 30),
            starting_nav=100000,
            ending_nav=105000,
            total_return_pct=0.05,
            max_drawdown_pct=0.02,
            avg_daily_pnl=166.67,
            best_day_pnl=1000,
            worst_day_pnl=-500,
            positive_days=20,
            negative_days=10,
        )
        assert m.total_return_pct == 0.05


class TestRepository:
    """Tests for repository functions."""

    def test_save_snapshot(self, tmp_db, sample_portfolio):
        """Test saving a portfolio snapshot."""
        snap = save_snapshot(sample_portfolio, db_path=tmp_db)
        assert snap.id is not None
        assert snap.net_assets == 29500.0
        assert len(snap.positions) == 2

    def test_save_and_retrieve(self, tmp_db, sample_portfolio):
        """Test save and retrieve round-trip."""
        save_snapshot(sample_portfolio, db_path=tmp_db)
        snapshots = get_snapshots(days=1, db_path=tmp_db)
        assert len(snapshots) == 1
        assert snapshots[0].net_assets == 29500.0

    def test_get_snapshots_empty(self, tmp_db):
        """Test retrieving snapshots from empty database."""
        init_db(tmp_db)
        snapshots = get_snapshots(days=30, db_path=tmp_db)
        assert snapshots == []

    def test_multiple_snapshots(self, tmp_db, sample_portfolio):
        """Test saving multiple snapshots."""
        save_snapshot(sample_portfolio, db_path=tmp_db)
        save_snapshot(sample_portfolio, db_path=tmp_db)
        save_snapshot(sample_portfolio, db_path=tmp_db)
        snapshots = get_snapshots(days=1, db_path=tmp_db)
        assert len(snapshots) == 3

    def test_get_performance(self, tmp_db, sample_portfolio):
        """Test performance metrics calculation."""
        save_snapshot(sample_portfolio, db_path=tmp_db)
        save_snapshot(sample_portfolio, db_path=tmp_db)
        metrics = get_performance(days=1, db_path=tmp_db)
        assert metrics is not None
        assert metrics.total_snapshots == 2
        assert metrics.total_return_pct == 0.0  # Same NAV

    def test_get_performance_empty(self, tmp_db):
        """Test performance metrics with no data."""
        init_db(tmp_db)
        metrics = get_performance(days=30, db_path=tmp_db)
        assert metrics is None

    def test_performance_max_drawdown(self, tmp_db):
        """Test max drawdown calculation."""
        # Create snapshots with varying NAVs
        conn = get_connection(tmp_db)
        navs = [100000, 105000, 102000, 98000, 103000]
        for _i, nav in enumerate(navs):
            conn.execute(
                "INSERT INTO portfolio_snapshots (timestamp, net_assets, cash, market_value, day_pnl, source) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (datetime.now().isoformat(), nav, 0, nav, 0, "test"),
            )
        conn.commit()
        conn.close()

        metrics = get_performance(days=1, db_path=tmp_db)
        assert metrics is not None
        # Max drawdown from 105000 to 98000 = 6.67%
        assert metrics.max_drawdown_pct == pytest.approx(
            (105000 - 98000) / 105000, abs=0.001
        )
