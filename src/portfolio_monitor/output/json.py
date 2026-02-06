"""JSON output formatting."""

from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..core.types import Alert, Portfolio, RiskMetrics


class CustomJSONEncoder(json.JSONEncoder):
    """JSON encoder that handles dataclasses, Decimal, datetime, and Enum."""

    def default(self, obj: Any) -> Any:
        if is_dataclass(obj) and not isinstance(obj, type):
            return asdict(obj)
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, Enum):
            return obj.value
        return super().default(obj)


class JSONFormatter:
    """JSON formatter for portfolio data."""

    def __init__(self, indent: int = 2, ensure_ascii: bool = False):
        self.indent = indent
        self.ensure_ascii = ensure_ascii

    def format_portfolio(self, portfolio: Portfolio) -> str:
        """Format portfolio as JSON."""
        data = {
            "summary": {
                "net_assets": float(portfolio.net_assets),
                "cash": float(portfolio.cash),
                "market_value": float(portfolio.market_value),
                "buying_power": float(portfolio.buying_power),
                "day_pnl": float(portfolio.day_pnl),
                "day_pnl_pct": portfolio.day_pnl_pct,
                "currency": portfolio.currency,
                "source": portfolio.source,
                "timestamp": portfolio.timestamp.isoformat() if portfolio.timestamp else None,
            },
            "positions": [
                {
                    "ticker": pos.symbol.ticker,
                    "exchange": pos.symbol.exchange.value,
                    "name": pos.name,
                    "quantity": float(pos.quantity),
                    "weight": pos.weight,
                    "avg_cost": float(pos.avg_cost) if pos.avg_cost else None,
                    "current_price": float(pos.current_price) if pos.current_price else None,
                    "market_value": float(pos.market_value),
                    "day_pnl": float(pos.day_pnl),
                    "day_pnl_pct": pos.day_pnl_pct,
                    "unrealized_pnl": float(pos.unrealized_pnl),
                    "unrealized_pnl_pct": pos.unrealized_pnl_pct,
                }
                for pos in portfolio.sorted_by_weight
            ],
        }
        return json.dumps(data, indent=self.indent, ensure_ascii=self.ensure_ascii)

    def format_risk_metrics(self, metrics: RiskMetrics) -> str:
        """Format risk metrics as JSON."""
        data = {
            "volatility": {
                "20d": metrics.volatility_20d,
                "60d": metrics.volatility_60d,
                "annualized": metrics.volatility_annualized,
            },
            "beta": {
                "spy": metrics.beta_spy,
                "qqq": metrics.beta_qqq,
            },
            "sharpe_ratio": metrics.sharpe_ratio,
            "risk_free_rate": metrics.risk_free_rate,
            "var": {
                "95_pct": metrics.var_95,
                "99_pct": metrics.var_99,
                "95_amount": float(metrics.var_95_amount) if metrics.var_95_amount else None,
                "99_amount": float(metrics.var_99_amount) if metrics.var_99_amount else None,
            },
            "concentration": {
                "hhi": metrics.hhi,
                "top_5_weight": metrics.top_5_concentration,
                "max_position_weight": metrics.max_position_weight,
            },
            "drawdown": {
                "max": metrics.max_drawdown,
                "current": metrics.current_drawdown,
            },
            "high_correlation_pairs": [
                {"ticker1": t1, "ticker2": t2, "correlation": c}
                for t1, t2, c in metrics.high_corr_pairs
            ],
            "timestamp": metrics.timestamp.isoformat() if metrics.timestamp else None,
        }
        return json.dumps(data, indent=self.indent, ensure_ascii=self.ensure_ascii)

    def format_alerts(self, alerts: list[Alert]) -> str:
        """Format alerts as JSON."""
        data = {
            "count": len(alerts),
            "alerts": [
                {
                    "type": alert.type.value,
                    "severity": alert.severity.value,
                    "title": alert.title,
                    "message": alert.message,
                    "ticker": alert.ticker,
                    "value": alert.value,
                    "threshold": alert.threshold,
                    "timestamp": alert.timestamp.isoformat(),
                    "metadata": alert.metadata,
                }
                for alert in alerts
            ],
        }
        return json.dumps(data, indent=self.indent, ensure_ascii=self.ensure_ascii)


def to_json(obj: Any, indent: int = 2) -> str:
    """Convert any object to JSON string.

    Handles dataclasses, Decimal, datetime, and Enum automatically.
    """
    return json.dumps(obj, cls=CustomJSONEncoder, indent=indent, ensure_ascii=False)
