"""Portfolio data export to CSV and JSON files."""

from __future__ import annotations

import csv
import io
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..core.types import Alert, Portfolio, RiskMetrics


def export_portfolio_csv(portfolio: Portfolio) -> str:
    """Export portfolio positions to CSV string."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "ticker", "exchange", "name", "quantity", "weight",
        "avg_cost", "current_price", "market_value",
        "day_pnl", "day_pnl_pct", "unrealized_pnl", "unrealized_pnl_pct",
    ])
    for pos in portfolio.sorted_by_weight:
        writer.writerow([
            pos.symbol.ticker,
            pos.symbol.exchange.value,
            pos.name,
            float(pos.quantity),
            f"{pos.weight:.4f}",
            float(pos.avg_cost) if pos.avg_cost else "",
            float(pos.current_price) if pos.current_price else "",
            float(pos.market_value),
            float(pos.day_pnl),
            f"{pos.day_pnl_pct:.4f}",
            float(pos.unrealized_pnl),
            f"{pos.unrealized_pnl_pct:.4f}",
        ])
    return output.getvalue()


def export_risk_csv(metrics: RiskMetrics) -> str:
    """Export risk metrics to CSV string."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["metric", "value"])
    rows = [
        ("volatility_20d", metrics.volatility_20d),
        ("volatility_60d", metrics.volatility_60d),
        ("volatility_annualized", metrics.volatility_annualized),
        ("beta_spy", metrics.beta_spy),
        ("beta_qqq", metrics.beta_qqq),
        ("sharpe_ratio", metrics.sharpe_ratio),
        ("sortino_ratio", getattr(metrics, "sortino_ratio", None)),
        ("risk_free_rate", metrics.risk_free_rate),
        ("var_95", metrics.var_95),
        ("var_99", metrics.var_99),
        ("cvar_95", getattr(metrics, "cvar_95", None)),
        ("cvar_99", getattr(metrics, "cvar_99", None)),
        ("hhi", metrics.hhi),
        ("max_drawdown", metrics.max_drawdown),
        ("current_drawdown", metrics.current_drawdown),
        ("rsi_portfolio", metrics.rsi_portfolio),
    ]
    for name, value in rows:
        writer.writerow([name, f"{value:.6f}" if value is not None else ""])
    return output.getvalue()


def export_alerts_csv(alerts: list[Alert]) -> str:
    """Export alerts to CSV string."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "type", "severity", "title", "message", "ticker",
        "value", "threshold", "timestamp",
    ])
    for alert in alerts:
        writer.writerow([
            alert.type.value,
            alert.severity.value,
            alert.title,
            alert.message,
            alert.ticker or "",
            alert.value if alert.value is not None else "",
            alert.threshold if alert.threshold is not None else "",
            alert.timestamp.isoformat(),
        ])
    return output.getvalue()


def export_portfolio_json(portfolio: Portfolio) -> str:
    """Export portfolio to JSON string (for file export)."""
    from .json import JSONFormatter
    return JSONFormatter().format_portfolio(portfolio)


def export_risk_json(metrics: RiskMetrics) -> str:
    """Export risk metrics to JSON string (for file export)."""
    from .json import JSONFormatter
    return JSONFormatter().format_risk_metrics(metrics)


def export_alerts_json(alerts: list[Alert]) -> str:
    """Export alerts to JSON string (for file export)."""
    from .json import JSONFormatter
    return JSONFormatter().format_alerts(alerts)
