"""Dollar-Cost Averaging (DCA) strategy signals."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

from ..market.data import get_history, get_price

if TYPE_CHECKING:
    from ..core.types import Portfolio


class SignalType(str, Enum):
    """DCA signal types."""
    REGULAR = "regular"  # Scheduled DCA
    DIP = "dip"  # Buy the dip signal
    REBALANCE = "rebalance"  # Portfolio rebalance needed


@dataclass
class DCASignal:
    """DCA buy signal."""
    ticker: str
    signal_type: SignalType
    current_price: float
    suggested_amount: float
    reason: str
    strength: float  # 0-1, higher = stronger signal


@dataclass
class DCAStrategy:
    """Dollar-Cost Averaging strategy configuration."""

    # Target allocations (ticker -> target weight)
    targets: dict[str, float]

    # DCA settings
    monthly_amount: float = 1000.0
    dip_threshold: float = 0.10  # 10% below recent high
    dip_amount_multiplier: float = 1.5  # Extra amount on dips
    rebalance_threshold: float = 0.05  # 5% deviation triggers rebalance

    def check_signals(self, portfolio: Portfolio) -> list[DCASignal]:
        """Check for DCA signals based on current portfolio.

        Args:
            portfolio: Current portfolio

        Returns:
            List of DCA signals
        """
        signals = []

        for ticker, target_weight in self.targets.items():
            # Get current weight
            pos = portfolio.get_position(ticker)
            current_weight = pos.weight if pos else 0.0

            # Check for rebalance signal
            if current_weight < target_weight - self.rebalance_threshold:
                deviation = target_weight - current_weight
                amount = float(portfolio.net_assets) * deviation

                signals.append(DCASignal(
                    ticker=ticker,
                    signal_type=SignalType.REBALANCE,
                    current_price=float(pos.current_price) if pos and pos.current_price else 0.0,
                    suggested_amount=amount,
                    reason=f"Below target by {deviation*100:.1f}%",
                    strength=min(deviation / self.rebalance_threshold, 1.0),
                ))

            # Check for dip signal
            dip_signal = self._check_dip(ticker)
            if dip_signal:
                signals.append(dip_signal)

        return signals

    def _check_dip(self, ticker: str) -> DCASignal | None:
        """Check if ticker is in a dip (below recent high)."""
        hist = get_history(ticker, period="3mo")
        if hist.empty:
            return None

        prices = hist["Close"]
        if len(prices) < 10:
            return None

        recent_high = float(prices.max())
        current_price = float(prices.iloc[-1])

        drawdown = (recent_high - current_price) / recent_high

        if drawdown >= self.dip_threshold:
            return DCASignal(
                ticker=ticker,
                signal_type=SignalType.DIP,
                current_price=current_price,
                suggested_amount=self.monthly_amount * self.dip_amount_multiplier,
                reason=f"Down {drawdown*100:.1f}% from 3-month high (${recent_high:.2f})",
                strength=min(drawdown / (self.dip_threshold * 2), 1.0),
            )

        return None

    def get_regular_allocation(self) -> dict[str, float]:
        """Get regular monthly DCA allocation amounts.

        Returns:
            Dictionary of ticker -> amount to invest
        """
        allocation = {}
        for ticker, weight in self.targets.items():
            allocation[ticker] = self.monthly_amount * weight
        return allocation


def check_dca_signals(
    portfolio: Portfolio,
    targets: dict[str, float],
    dip_threshold: float = 0.10,
) -> list[DCASignal]:
    """Quick function to check for DCA signals.

    Args:
        portfolio: Current portfolio
        targets: Target allocations
        dip_threshold: Dip detection threshold

    Returns:
        List of DCA signals
    """
    strategy = DCAStrategy(
        targets=targets,
        dip_threshold=dip_threshold,
    )
    return strategy.check_signals(portfolio)


def calculate_dca_performance(
    ticker: str,
    monthly_amount: float,
    months: int = 12,
) -> dict:
    """Calculate historical DCA performance.

    Args:
        ticker: Ticker to analyze
        monthly_amount: Monthly investment amount
        months: Number of months to analyze

    Returns:
        Performance metrics
    """
    hist = get_history(ticker, period=f"{months}mo")
    if hist.empty:
        return {}

    # Simulate monthly purchases on first trading day of each month
    prices = hist["Close"].resample("MS").first().dropna()

    total_invested = 0.0
    total_shares = 0.0

    for price in prices:
        shares = monthly_amount / float(price)
        total_shares += shares
        total_invested += monthly_amount

    current_price = get_price(ticker) or float(prices.iloc[-1])
    current_value = total_shares * current_price
    total_return = (current_value - total_invested) / total_invested if total_invested > 0 else 0

    avg_cost = total_invested / total_shares if total_shares > 0 else 0

    return {
        "ticker": ticker,
        "months": len(prices),
        "total_invested": total_invested,
        "total_shares": total_shares,
        "avg_cost_basis": avg_cost,
        "current_price": current_price,
        "current_value": current_value,
        "total_return": total_return,
        "total_return_pct": total_return * 100,
    }
