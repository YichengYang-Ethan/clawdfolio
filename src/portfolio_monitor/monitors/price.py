"""Price movement monitoring and alerts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from ..core.types import Alert, AlertSeverity, AlertType

if TYPE_CHECKING:
    from ..core.config import Config
    from ..core.types import Portfolio


@dataclass
class PriceAlert:
    """Price alert result."""
    ticker: str
    price_change_pct: float
    weight: float
    is_gain: bool
    threshold: float
    rank: int


@dataclass
class PriceMonitor:
    """Monitor for price movement alerts."""

    # Thresholds
    top10_threshold: float = 0.05  # 5% for top 10
    other_threshold: float = 0.10  # 10% for others
    pnl_trigger: float = 500.0  # Absolute P&L trigger

    # State for deduplication
    last_alerts: dict[str, dict] = field(default_factory=dict)

    @classmethod
    def from_config(cls, config: Config) -> PriceMonitor:
        """Create monitor from config."""
        return cls(
            top10_threshold=config.alerts.single_stock_threshold_top10,
            other_threshold=config.alerts.single_stock_threshold_other,
            pnl_trigger=config.alerts.pnl_trigger,
        )

    def check_portfolio(self, portfolio: Portfolio) -> list[Alert]:
        """Check portfolio for price alerts.

        Args:
            portfolio: Portfolio to check

        Returns:
            List of triggered alerts
        """
        alerts = []

        # Sort positions by weight
        sorted_positions = portfolio.sorted_by_weight

        for i, pos in enumerate(sorted_positions, start=1):
            threshold = self.top10_threshold if i <= 10 else self.other_threshold
            day_pct = pos.day_pnl_pct

            if abs(day_pct) >= threshold:
                severity = AlertSeverity.WARNING
                if abs(day_pct) >= threshold * 2:
                    severity = AlertSeverity.CRITICAL

                direction = "up" if day_pct > 0 else "down"
                alerts.append(Alert(
                    type=AlertType.PRICE_MOVE,
                    severity=severity,
                    title=f"{pos.symbol.ticker} {direction} {abs(day_pct)*100:.1f}%",
                    message=self._format_price_message(pos, i),
                    ticker=pos.symbol.ticker,
                    value=day_pct,
                    threshold=threshold,
                    metadata={"rank": i, "weight": pos.weight},
                ))

        # Check total P&L
        if abs(float(portfolio.day_pnl)) >= self.pnl_trigger:
            is_gain = portfolio.day_pnl > 0
            severity = AlertSeverity.WARNING
            if abs(float(portfolio.day_pnl)) >= self.pnl_trigger * 2:
                severity = AlertSeverity.CRITICAL

            alerts.append(Alert(
                type=AlertType.PNL_THRESHOLD,
                severity=severity,
                title=f"Portfolio {'gained' if is_gain else 'lost'} ${abs(portfolio.day_pnl):,.0f} today",
                message=self._format_pnl_message(portfolio, is_gain),
                value=float(portfolio.day_pnl),
                threshold=self.pnl_trigger,
            ))

        return alerts

    def _format_price_message(self, pos, rank: int) -> str:
        """Format price alert message."""
        direction = "up" if pos.day_pnl_pct > 0 else "down"
        return (
            f"{pos.symbol.ticker} (rank #{rank}, {pos.weight*100:.1f}% of portfolio) "
            f"is {direction} {abs(pos.day_pnl_pct)*100:.1f}% today. "
            f"Day P&L: ${float(pos.day_pnl):,.2f}"
        )

    def _format_pnl_message(self, portfolio: Portfolio, is_gain: bool) -> str:
        """Format P&L alert message."""
        # Get top contributors
        sorted_pos = sorted(
            portfolio.positions,
            key=lambda p: abs(float(p.day_pnl)),
            reverse=True
        )[:3]

        contributors = []
        for p in sorted_pos:
            direction = "+" if p.day_pnl > 0 else ""
            contributors.append(f"{p.symbol.ticker}: {direction}${float(p.day_pnl):,.0f}")

        return (
            f"Total day P&L: {'+'if is_gain else '-'}${abs(portfolio.day_pnl):,.2f} "
            f"({portfolio.day_pnl_pct*100:+.2f}%)\n"
            f"Top contributors: {', '.join(contributors)}"
        )


def detect_price_alerts(
    portfolio: Portfolio,
    top10_threshold: float = 0.05,
    other_threshold: float = 0.10,
) -> list[PriceAlert]:
    """Quick function to detect price alerts.

    Args:
        portfolio: Portfolio to check
        top10_threshold: Threshold for top 10 positions
        other_threshold: Threshold for other positions

    Returns:
        List of price alerts
    """
    alerts = []
    sorted_positions = portfolio.sorted_by_weight

    for i, pos in enumerate(sorted_positions, start=1):
        threshold = top10_threshold if i <= 10 else other_threshold
        day_pct = pos.day_pnl_pct

        if abs(day_pct) >= threshold:
            alerts.append(PriceAlert(
                ticker=pos.symbol.ticker,
                price_change_pct=day_pct,
                weight=pos.weight,
                is_gain=day_pct > 0,
                threshold=threshold,
                rank=i,
            ))

    return alerts


def detect_gap(
    prev_close: float,
    open_price: float,
    threshold: float = 0.02,
) -> tuple[bool, float]:
    """Detect gap up/down at market open.

    Args:
        prev_close: Previous close price
        open_price: Today's open price
        threshold: Gap threshold (default 2%)

    Returns:
        Tuple of (is_gap, gap_percentage)
    """
    if prev_close <= 0:
        return False, 0.0

    gap_pct = (open_price - prev_close) / prev_close
    is_gap = abs(gap_pct) >= threshold

    return is_gap, gap_pct
