"""Trading calendar utilities."""

from __future__ import annotations

from datetime import date, timedelta
from functools import lru_cache

# US market holidays (fixed dates - actual holidays may vary by year)
# This is a simplified version; for production, consider using a library
# like `exchange_calendars` or `pandas_market_calendars`
US_HOLIDAYS_2024 = {
    date(2024, 1, 1),  # New Year's Day
    date(2024, 1, 15),  # MLK Day
    date(2024, 2, 19),  # Presidents Day
    date(2024, 3, 29),  # Good Friday
    date(2024, 5, 27),  # Memorial Day
    date(2024, 6, 19),  # Juneteenth
    date(2024, 7, 4),  # Independence Day
    date(2024, 9, 2),  # Labor Day
    date(2024, 11, 28),  # Thanksgiving
    date(2024, 12, 25),  # Christmas
}

US_HOLIDAYS_2025 = {
    date(2025, 1, 1),  # New Year's Day
    date(2025, 1, 20),  # MLK Day
    date(2025, 2, 17),  # Presidents Day
    date(2025, 4, 18),  # Good Friday
    date(2025, 5, 26),  # Memorial Day
    date(2025, 6, 19),  # Juneteenth
    date(2025, 7, 4),  # Independence Day
    date(2025, 9, 1),  # Labor Day
    date(2025, 11, 27),  # Thanksgiving
    date(2025, 12, 25),  # Christmas
}

US_HOLIDAYS_2026 = {
    date(2026, 1, 1),  # New Year's Day
    date(2026, 1, 19),  # MLK Day
    date(2026, 2, 16),  # Presidents Day
    date(2026, 4, 3),  # Good Friday
    date(2026, 5, 25),  # Memorial Day
    date(2026, 6, 19),  # Juneteenth
    date(2026, 7, 3),  # Independence Day (observed)
    date(2026, 9, 7),  # Labor Day
    date(2026, 11, 26),  # Thanksgiving
    date(2026, 12, 25),  # Christmas
}

US_HOLIDAYS_2027 = {
    date(2027, 1, 1),  # New Year's Day
    date(2027, 1, 18),  # MLK Day
    date(2027, 2, 15),  # Presidents Day
    date(2027, 3, 26),  # Good Friday
    date(2027, 5, 31),  # Memorial Day
    date(2027, 6, 18),  # Juneteenth (observed)
    date(2027, 7, 5),  # Independence Day (observed)
    date(2027, 9, 6),  # Labor Day
    date(2027, 11, 25),  # Thanksgiving
    date(2027, 12, 24),  # Christmas (observed)
}

US_HOLIDAYS = US_HOLIDAYS_2024 | US_HOLIDAYS_2025 | US_HOLIDAYS_2026 | US_HOLIDAYS_2027


def _nth_weekday(year: int, month: int, weekday: int, n: int) -> date:
    """Get the nth occurrence of a weekday in a month.
    weekday: 0=Monday, 6=Sunday. n: 1-based (1=first, -1=last).
    """
    if n > 0:
        first = date(year, month, 1)
        day_offset = (weekday - first.weekday()) % 7
        result = first + timedelta(days=day_offset + (n - 1) * 7)
        return result
    else:
        # Last occurrence
        if month == 12:
            last = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            last = date(year, month + 1, 1) - timedelta(days=1)
        day_offset = (last.weekday() - weekday) % 7
        return last - timedelta(days=day_offset)


def _easter(year: int) -> date:
    """Anonymous Gregorian Easter algorithm."""
    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l = (32 + 2 * e + 2 * i - h - k) % 7  # noqa: E741
    m = (a + 11 * h + 22 * l) // 451
    month, day = divmod(h + l - 7 * m + 114, 31)
    return date(year, month, day + 1)


def _observed_holiday(d: date) -> date:
    """Adjust holiday to observed date (Sat->Fri, Sun->Mon)."""
    if d.weekday() == 5:  # Saturday
        return d - timedelta(days=1)
    elif d.weekday() == 6:  # Sunday
        return d + timedelta(days=1)
    return d


def _generate_us_holidays(year: int) -> set[date]:
    """Generate US stock market holidays for any year algorithmically."""
    holidays = set()

    # New Year's Day (Jan 1, observed)
    holidays.add(_observed_holiday(date(year, 1, 1)))

    # MLK Day (3rd Monday in January)
    holidays.add(_nth_weekday(year, 1, 0, 3))  # 0=Monday

    # Presidents Day (3rd Monday in February)
    holidays.add(_nth_weekday(year, 2, 0, 3))

    # Good Friday (2 days before Easter)
    holidays.add(_easter(year) - timedelta(days=2))

    # Memorial Day (last Monday in May)
    holidays.add(_nth_weekday(year, 5, 0, -1))

    # Juneteenth (June 19, observed)
    holidays.add(_observed_holiday(date(year, 6, 19)))

    # Independence Day (July 4, observed)
    holidays.add(_observed_holiday(date(year, 7, 4)))

    # Labor Day (1st Monday in September)
    holidays.add(_nth_weekday(year, 9, 0, 1))

    # Thanksgiving (4th Thursday in November)
    holidays.add(_nth_weekday(year, 11, 3, 4))  # 3=Thursday

    # Christmas (Dec 25, observed)
    holidays.add(_observed_holiday(date(year, 12, 25)))

    return holidays


_holiday_cache: dict[int, set[date]] = {}


def _get_holidays_for_year(year: int) -> set[date]:
    """Get holidays for a year, with caching."""
    if year not in _holiday_cache:
        _holiday_cache[year] = _generate_us_holidays(year)
    return _holiday_cache[year]


def is_weekend(d: date) -> bool:
    """Check if date is a weekend."""
    return d.weekday() >= 5  # Saturday = 5, Sunday = 6


def is_us_holiday(d: date) -> bool:
    """Check if date is a US market holiday."""
    # Fast path: check hardcoded sets first
    if d in US_HOLIDAYS:
        return True
    # Dynamic generation for any year
    return d in _get_holidays_for_year(d.year)


def is_trading_day(d: date | None = None, market: str = "US") -> bool:
    """Check if date is a trading day.

    Args:
        d: Date to check (defaults to today)
        market: Market code (currently only US supported)

    Returns:
        True if it's a trading day
    """
    if d is None:
        d = date.today()

    if is_weekend(d):
        return False

    if market.upper() == "US":
        return not is_us_holiday(d)

    # Default: assume weekdays are trading days
    return True


def next_trading_day(d: date | None = None, market: str = "US") -> date:
    """Get the next trading day after the given date.

    Args:
        d: Start date (defaults to today)
        market: Market code

    Returns:
        Next trading day
    """
    if d is None:
        d = date.today()

    d = d + timedelta(days=1)
    while not is_trading_day(d, market):
        d += timedelta(days=1)

    return d


def prev_trading_day(d: date | None = None, market: str = "US") -> date:
    """Get the previous trading day before the given date.

    Args:
        d: Start date (defaults to today)
        market: Market code

    Returns:
        Previous trading day
    """
    if d is None:
        d = date.today()

    d = d - timedelta(days=1)
    while not is_trading_day(d, market):
        d -= timedelta(days=1)

    return d


def trading_days_between(start: date, end: date, market: str = "US") -> list[date]:
    """Get all trading days between two dates (inclusive).

    Args:
        start: Start date
        end: End date
        market: Market code

    Returns:
        List of trading days
    """
    days = []
    current = start

    while current <= end:
        if is_trading_day(current, market):
            days.append(current)
        current += timedelta(days=1)

    return days


def trading_days_count(start: date, end: date, market: str = "US") -> int:
    """Count trading days between two dates.

    Args:
        start: Start date
        end: End date
        market: Market code

    Returns:
        Number of trading days
    """
    return len(trading_days_between(start, end, market))


@lru_cache(maxsize=4)
def get_current_year_holidays(market: str = "US") -> set[date]:
    """Get holidays for the current year (cached)."""
    current_year = date.today().year
    if market.upper() == "US":
        return _get_holidays_for_year(current_year)
    return set()


def days_until_next_holiday(market: str = "US") -> int | None:
    """Get days until the next market holiday.

    Returns:
        Days until next holiday, or None if unknown
    """
    today = date.today()
    holidays = get_current_year_holidays(market)

    future_holidays = [h for h in holidays if h > today]
    if not future_holidays:
        return None

    next_holiday = min(future_holidays)
    return (next_holiday - today).days
