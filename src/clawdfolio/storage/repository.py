"""Repository functions for saving and querying portfolio snapshots."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from .database import get_connection
from .models import PerformanceMetrics, PortfolioSnapshot, PositionSnapshot

if TYPE_CHECKING:
    from ..core.types import Portfolio


def save_snapshot(
    portfolio: Portfolio,
    db_path: str | None = None,
) -> PortfolioSnapshot:
    """Save a portfolio snapshot to the database.

    Args:
        portfolio: Portfolio to snapshot.
        db_path: Optional database path override.

    Returns:
        The saved PortfolioSnapshot with id populated.
    """
    now = datetime.now()
    conn = get_connection(db_path)
    try:
        cursor = conn.execute(
            "INSERT INTO portfolio_snapshots (timestamp, net_assets, cash, market_value, day_pnl, source) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                now.isoformat(),
                float(portfolio.net_assets),
                float(portfolio.cash),
                float(portfolio.market_value),
                float(portfolio.day_pnl),
                portfolio.source,
            ),
        )
        snapshot_id = cursor.lastrowid

        positions: list[PositionSnapshot] = []
        for pos in portfolio.positions:
            conn.execute(
                "INSERT INTO position_snapshots (snapshot_id, ticker, quantity, avg_cost, market_value, weight) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    snapshot_id,
                    pos.symbol.ticker,
                    float(pos.quantity),
                    float(pos.avg_cost or 0),
                    float(pos.market_value),
                    pos.weight,
                ),
            )
            positions.append(
                PositionSnapshot(
                    ticker=pos.symbol.ticker,
                    quantity=float(pos.quantity),
                    avg_cost=float(pos.avg_cost or 0),
                    market_value=float(pos.market_value),
                    weight=pos.weight,
                    snapshot_id=snapshot_id,
                )
            )

        conn.commit()
        return PortfolioSnapshot(
            id=snapshot_id,
            timestamp=now,
            net_assets=float(portfolio.net_assets),
            cash=float(portfolio.cash),
            market_value=float(portfolio.market_value),
            day_pnl=float(portfolio.day_pnl),
            source=portfolio.source,
            positions=positions,
        )
    finally:
        conn.close()


def get_snapshots(
    days: int = 30,
    db_path: str | None = None,
) -> list[PortfolioSnapshot]:
    """Retrieve portfolio snapshots for the last N days.

    Args:
        days: Number of days to look back.
        db_path: Optional database path override.

    Returns:
        List of PortfolioSnapshot, oldest first.
    """
    since = (datetime.now() - timedelta(days=days)).isoformat()
    conn = get_connection(db_path)
    try:
        rows = conn.execute(
            "SELECT id, timestamp, net_assets, cash, market_value, day_pnl, source "
            "FROM portfolio_snapshots WHERE timestamp >= ? ORDER BY timestamp ASC",
            (since,),
        ).fetchall()

        snapshots: list[PortfolioSnapshot] = []
        for row in rows:
            snap = PortfolioSnapshot(
                id=row["id"],
                timestamp=datetime.fromisoformat(row["timestamp"]),
                net_assets=row["net_assets"],
                cash=row["cash"],
                market_value=row["market_value"],
                day_pnl=row["day_pnl"],
                source=row["source"],
            )
            snapshots.append(snap)

        return snapshots
    finally:
        conn.close()


def get_performance(
    days: int = 30,
    db_path: str | None = None,
) -> PerformanceMetrics | None:
    """Calculate performance metrics from snapshot history.

    Args:
        days: Number of days to analyze.
        db_path: Optional database path override.

    Returns:
        PerformanceMetrics or None if no data.
    """
    snapshots = get_snapshots(days=days, db_path=db_path)
    if not snapshots:
        return None

    navs = [s.net_assets for s in snapshots]
    pnls = [s.day_pnl for s in snapshots]
    positive = sum(1 for p in pnls if p > 0)
    negative = sum(1 for p in pnls if p < 0)

    # Max drawdown from peak NAV
    peak = navs[0]
    max_dd = 0.0
    for nav in navs:
        if nav > peak:
            peak = nav
        dd = (peak - nav) / peak if peak > 0 else 0.0
        if dd > max_dd:
            max_dd = dd

    starting = navs[0]
    ending = navs[-1]
    total_return = (ending - starting) / starting if starting > 0 else 0.0

    return PerformanceMetrics(
        total_snapshots=len(snapshots),
        first_date=snapshots[0].timestamp,
        last_date=snapshots[-1].timestamp,
        starting_nav=starting,
        ending_nav=ending,
        total_return_pct=total_return,
        max_drawdown_pct=max_dd,
        avg_daily_pnl=sum(pnls) / len(pnls) if pnls else 0.0,
        best_day_pnl=max(pnls) if pnls else 0.0,
        worst_day_pnl=min(pnls) if pnls else 0.0,
        positive_days=positive,
        negative_days=negative,
    )
