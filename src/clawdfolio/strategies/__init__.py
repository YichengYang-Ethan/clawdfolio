"""Investment strategies."""

from .covered_call import (
    CCAction,
    CoveredCallSignal,
    CoveredCallStrategy,
    check_cc_signals,
    get_cc_recommendation,
)
from .dca import DCASignal, DCAStrategy, check_dca_signals
from .rebalance import (
    RebalanceAction,
    TargetAllocation,
    calculate_rebalance,
    propose_dca_allocation,
)

__all__ = [
    # Covered Call
    "CCAction",
    "CoveredCallSignal",
    "CoveredCallStrategy",
    "check_cc_signals",
    "get_cc_recommendation",
    # DCA
    "DCAStrategy",
    "DCASignal",
    "check_dca_signals",
    # Rebalance
    "TargetAllocation",
    "RebalanceAction",
    "calculate_rebalance",
    "propose_dca_allocation",
]
