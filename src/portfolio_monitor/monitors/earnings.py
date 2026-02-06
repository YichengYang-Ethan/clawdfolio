"""Earnings calendar monitoring."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import TYPE_CHECKING

from ..core.types import Alert, AlertSeverity, AlertType
from ..market.data import get_earnings_date

if TYPE_CHECKING:
    from ..core.types import Portfolio


@dataclass
class EarningsEvent:
    """Upcoming earnings event."""
    ticker: str
    date: date
    timing: str  # BMO, AMC, TBD
    days_until: int
    weight: float


@dataclass
class EarningsMonitor:
    """Monitor for upcoming earnings in portfolio."""

    # Alert window (days before earnings)
    alert_days: int = 7

    def check_portfolio(self, portfolio: Portfolio) -> list[Alert]:
        """Check portfolio for upcoming earnings.

        Args:
            portfolio: Portfolio to check

        Returns:
            List of earnings alerts
        """
        alerts = []
        events = get_upcoming_earnings(portfolio, days_ahead=self.alert_days)

        for event in events:
            severity = AlertSeverity.INFO
            if event.days_until <= 1:
                severity = AlertSeverity.WARNING
            if event.weight >= 0.10:  # Top holding
                severity = AlertSeverity.WARNING if severity == AlertSeverity.INFO else severity

            timing_str = {
                "BMO": "before market open",
                "AMC": "after market close",
                "TBD": "(timing TBD)",
            }.get(event.timing, "")

            if event.days_until == 0:
                title = f"{event.ticker} reports earnings TODAY {timing_str}"
            elif event.days_until == 1:
                title = f"{event.ticker} reports earnings TOMORROW {timing_str}"
            else:
                title = f"{event.ticker} reports earnings in {event.days_until} days"

            alerts.append(Alert(
                type=AlertType.EARNINGS,
                severity=severity,
                title=title,
                message=f"{event.ticker} ({event.weight*100:.1f}% of portfolio) "
                        f"reports on {event.date.strftime('%b %d')} {event.timing}",
                ticker=event.ticker,
                metadata={
                    "earnings_date": event.date.isoformat(),
                    "timing": event.timing,
                    "days_until": event.days_until,
                    "weight": event.weight,
                },
            ))

        return alerts


def get_upcoming_earnings(
    portfolio: Portfolio,
    days_ahead: int = 14,
) -> list[EarningsEvent]:
    """Get upcoming earnings for portfolio holdings.

    Args:
        portfolio: Portfolio to check
        days_ahead: Number of days to look ahead

    Returns:
        List of upcoming earnings events, sorted by date
    """
    events = []
    today = date.today()
    cutoff = today + timedelta(days=days_ahead)

    for pos in portfolio.positions:
        ticker = pos.symbol.ticker
        result = get_earnings_date(ticker)

        if result is None:
            continue

        earnings_dt, timing = result
        earnings_date = earnings_dt.date() if isinstance(earnings_dt, datetime) else earnings_dt

        if today <= earnings_date <= cutoff:
            days_until = (earnings_date - today).days
            events.append(EarningsEvent(
                ticker=ticker,
                date=earnings_date,
                timing=timing,
                days_until=days_until,
                weight=pos.weight,
            ))

    # Sort by date, then by weight (for same day)
    events.sort(key=lambda e: (e.date, -e.weight))

    return events


def format_earnings_calendar(events: list[EarningsEvent]) -> str:
    """Format earnings events as a readable calendar.

    Args:
        events: List of earnings events

    Returns:
        Formatted string
    """
    if not events:
        return "No upcoming earnings in the next 2 weeks."

    lines = ["Upcoming Earnings:", ""]
    current_date = None

    for event in events:
        if event.date != current_date:
            current_date = event.date
            date_str = event.date.strftime("%a, %b %d")
            if event.days_until == 0:
                date_str += " (TODAY)"
            elif event.days_until == 1:
                date_str += " (Tomorrow)"
            lines.append(f"{date_str}")

        timing_emoji = {"BMO": "AM", "AMC": "PM", "TBD": "?"}.get(event.timing, "?")
        lines.append(
            f"  [{timing_emoji}] {event.ticker} ({event.weight*100:.1f}%)"
        )

    return "\n".join(lines)
