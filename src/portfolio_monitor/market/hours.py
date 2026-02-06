"""Market hours and trading session utilities."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta
from enum import Enum
from typing import ClassVar, NamedTuple
from zoneinfo import ZoneInfo


class MarketStatus(str, Enum):
    """Market status states."""

    PRE_MARKET = "pre_market"
    OPEN = "open"
    AFTER_HOURS = "after_hours"
    CLOSED = "closed"


class MarketSession(NamedTuple):
    """Market trading session times."""

    pre_market_open: time
    market_open: time
    market_close: time
    after_hours_close: time


@dataclass
class MarketHours:
    """Market hours configuration for a specific market."""

    market: str
    timezone: ZoneInfo
    session: MarketSession

    # Class-level market constants (defined after class)
    US: ClassVar[MarketHours]
    HK: ClassVar[MarketHours]
    CN: ClassVar[MarketHours]

    def now(self) -> datetime:
        """Get current time in market timezone."""
        return datetime.now(self.timezone)

    def is_pre_market(self, dt: datetime | None = None) -> bool:
        """Check if currently in pre-market session."""
        dt = dt or self.now()
        t = dt.time()
        return self.session.pre_market_open <= t < self.session.market_open

    def is_market_open(self, dt: datetime | None = None) -> bool:
        """Check if market is currently open (regular hours)."""
        dt = dt or self.now()
        t = dt.time()
        return self.session.market_open <= t < self.session.market_close

    def is_after_hours(self, dt: datetime | None = None) -> bool:
        """Check if currently in after-hours session."""
        dt = dt or self.now()
        t = dt.time()
        return self.session.market_close <= t < self.session.after_hours_close

    def is_extended_hours(self, dt: datetime | None = None) -> bool:
        """Check if in any extended hours session (pre or after)."""
        return self.is_pre_market(dt) or self.is_after_hours(dt)

    def get_status(self, dt: datetime | None = None) -> MarketStatus:
        """Get current market status."""
        dt = dt or self.now()
        t = dt.time()

        if self.session.pre_market_open <= t < self.session.market_open:
            return MarketStatus.PRE_MARKET
        elif self.session.market_open <= t < self.session.market_close:
            return MarketStatus.OPEN
        elif self.session.market_close <= t < self.session.after_hours_close:
            return MarketStatus.AFTER_HOURS
        else:
            return MarketStatus.CLOSED

    def time_to_open(self, dt: datetime | None = None) -> timedelta | None:
        """Get time until market opens. Returns None if already open."""
        dt = dt or self.now()
        if self.is_market_open(dt):
            return None

        open_time = datetime.combine(dt.date(), self.session.market_open)
        open_time = open_time.replace(tzinfo=self.timezone)

        if dt.time() >= self.session.market_close:
            # After close, next open is tomorrow
            open_time += timedelta(days=1)

        return open_time - dt

    def time_to_close(self, dt: datetime | None = None) -> timedelta | None:
        """Get time until market closes. Returns None if already closed."""
        dt = dt or self.now()
        if not self.is_market_open(dt):
            return None

        close_time = datetime.combine(dt.date(), self.session.market_close)
        close_time = close_time.replace(tzinfo=self.timezone)

        return close_time - dt


# Define market constants
MarketHours.US = MarketHours(
    market="US",
    timezone=ZoneInfo("America/New_York"),
    session=MarketSession(
        pre_market_open=time(4, 0),
        market_open=time(9, 30),
        market_close=time(16, 0),
        after_hours_close=time(20, 0),
    ),
)

MarketHours.HK = MarketHours(
    market="HK",
    timezone=ZoneInfo("Asia/Hong_Kong"),
    session=MarketSession(
        pre_market_open=time(9, 0),
        market_open=time(9, 30),
        market_close=time(16, 0),
        after_hours_close=time(16, 10),
    ),
)

MarketHours.CN = MarketHours(
    market="CN",
    timezone=ZoneInfo("Asia/Shanghai"),
    session=MarketSession(
        pre_market_open=time(9, 15),
        market_open=time(9, 30),
        market_close=time(15, 0),
        after_hours_close=time(15, 0),
    ),
)


# Convenience functions for US market (most common use case)
def is_market_open(market: str = "US") -> bool:
    """Check if market is open (regular hours)."""
    hours = _get_market_hours(market)
    return hours.is_market_open()


def get_market_status(market: str = "US") -> MarketStatus:
    """Get current market status."""
    hours = _get_market_hours(market)
    return hours.get_status()


def time_to_open(market: str = "US") -> timedelta | None:
    """Get time until market opens."""
    hours = _get_market_hours(market)
    return hours.time_to_open()


def time_to_close(market: str = "US") -> timedelta | None:
    """Get time until market closes."""
    hours = _get_market_hours(market)
    return hours.time_to_close()


def _get_market_hours(market: str) -> MarketHours:
    """Get MarketHours for a market code."""
    markets: dict[str, MarketHours] = {
        "US": MarketHours.US,
        "HK": MarketHours.HK,
        "CN": MarketHours.CN,
    }
    return markets.get(market.upper()) or MarketHours.US
