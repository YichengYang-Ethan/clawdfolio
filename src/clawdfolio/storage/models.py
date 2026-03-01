"""Data models for portfolio history storage."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class PositionSnapshot:
    """Snapshot of a single position at a point in time."""

    ticker: str
    quantity: float
    avg_cost: float
    market_value: float
    weight: float
    id: int | None = None
    snapshot_id: int | None = None


@dataclass
class PortfolioSnapshot:
    """Snapshot of the entire portfolio at a point in time."""

    timestamp: datetime
    net_assets: float
    cash: float
    market_value: float
    day_pnl: float
    source: str = ""
    id: int | None = None
    positions: list[PositionSnapshot] = field(default_factory=list)


@dataclass
class PerformanceMetrics:
    """Calculated performance metrics from snapshot history."""

    total_snapshots: int
    first_date: datetime | None
    last_date: datetime | None
    starting_nav: float
    ending_nav: float
    total_return_pct: float
    max_drawdown_pct: float
    avg_daily_pnl: float
    best_day_pnl: float
    worst_day_pnl: float
    positive_days: int
    negative_days: int
