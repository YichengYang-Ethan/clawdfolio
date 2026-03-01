"""Portfolio rebalancing analysis and recommendations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..core.types import Portfolio


@dataclass
class TargetAllocation:
    """A target weight for a ticker."""

    ticker: str
    weight: float  # 0.0 to 1.0


@dataclass
class RebalanceAction:
    """A recommended rebalance action."""

    ticker: str
    current_weight: float
    target_weight: float
    deviation: float  # current - target
    status: str  # "OVERWEIGHT", "UNDERWEIGHT", "ON_TARGET"
    dollar_amount: float  # positive = buy, negative = sell
    shares: int  # approximate shares to trade


def calculate_rebalance(
    portfolio: Portfolio,
    targets: list[TargetAllocation],
    tolerance: float = 0.03,
) -> list[RebalanceAction]:
    """Calculate rebalance actions to align portfolio with target allocations.

    Args:
        portfolio: Current portfolio.
        targets: Target allocations.
        tolerance: Deviation tolerance before flagging (default 3%).

    Returns:
        List of RebalanceAction sorted by absolute deviation descending.
    """
    net_assets = float(portfolio.net_assets)
    if net_assets <= 0:
        return []

    # Build current weight lookup
    current_weights: dict[str, float] = {}
    current_prices: dict[str, float] = {}
    for pos in portfolio.positions:
        current_weights[pos.symbol.ticker] = pos.weight
        current_prices[pos.symbol.ticker] = float(pos.current_price or 0)

    actions: list[RebalanceAction] = []
    for target in targets:
        current_w = current_weights.get(target.ticker, 0.0)
        deviation = current_w - target.weight
        dollar_diff = -deviation * net_assets  # positive = need to buy

        price = current_prices.get(target.ticker, 0.0)
        shares = int(dollar_diff / price) if price > 0 else 0

        if abs(deviation) <= tolerance:
            status = "ON_TARGET"
        elif deviation > 0:
            status = "OVERWEIGHT"
        else:
            status = "UNDERWEIGHT"

        actions.append(
            RebalanceAction(
                ticker=target.ticker,
                current_weight=current_w,
                target_weight=target.weight,
                deviation=deviation,
                status=status,
                dollar_amount=dollar_diff,
                shares=shares,
            )
        )

    actions.sort(key=lambda a: abs(a.deviation), reverse=True)
    return actions


def propose_dca_allocation(
    portfolio: Portfolio,
    targets: list[TargetAllocation],
    amount: float,
) -> list[RebalanceAction]:
    """Propose how to allocate a DCA amount to reduce target deviations.

    Only produces buy actions — never suggests selling.

    Args:
        portfolio: Current portfolio.
        targets: Target allocations.
        amount: Dollar amount to invest.

    Returns:
        List of RebalanceAction with positive dollar_amount (buys only).
    """
    net_assets = float(portfolio.net_assets)
    if net_assets <= 0 or amount <= 0:
        return []

    # Future NAV after adding cash
    future_nav = net_assets + amount

    current_weights: dict[str, float] = {}
    current_prices: dict[str, float] = {}
    current_values: dict[str, float] = {}
    for pos in portfolio.positions:
        current_weights[pos.symbol.ticker] = pos.weight
        current_prices[pos.symbol.ticker] = float(pos.current_price or 0)
        current_values[pos.symbol.ticker] = float(pos.market_value)

    # Calculate underweight tickers and how much to buy
    underweight: list[tuple[str, float, float]] = []  # (ticker, shortfall_ratio, target_weight)
    for target in targets:
        current_value = current_values.get(target.ticker, 0.0)
        target_value = target.weight * future_nav
        shortfall = target_value - current_value
        if shortfall > 0:
            underweight.append((target.ticker, shortfall, target.weight))

    if not underweight:
        return []

    total_shortfall = sum(s for _, s, _ in underweight)
    actions: list[RebalanceAction] = []
    for ticker, shortfall, target_w in underweight:
        # Allocate proportionally to shortfall
        alloc = amount * (shortfall / total_shortfall) if total_shortfall > 0 else 0
        price = current_prices.get(ticker, 0.0)
        shares = int(alloc / price) if price > 0 else 0
        current_w = current_weights.get(ticker, 0.0)

        actions.append(
            RebalanceAction(
                ticker=ticker,
                current_weight=current_w,
                target_weight=target_w,
                deviation=current_w - target_w,
                status="BUY",
                dollar_amount=alloc,
                shares=shares,
            )
        )

    actions.sort(key=lambda a: a.dollar_amount, reverse=True)
    return actions
