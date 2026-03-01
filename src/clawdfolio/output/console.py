"""Console output formatting using Rich."""

from __future__ import annotations

from typing import TYPE_CHECKING

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

if TYPE_CHECKING:
    from ..core.types import Alert, Portfolio, RiskMetrics
    from ..storage.models import PerformanceMetrics, PortfolioSnapshot
    from ..strategies.rebalance import RebalanceAction


def _format_money(value: float, decimals: int = 2) -> str:
    """Format money with color coding."""
    sign = "+" if value > 0 else ""
    return f"{sign}${value:,.{decimals}f}"


def _format_pct(value: float, decimals: int = 2) -> str:
    """Format percentage with color coding."""
    sign = "+" if value > 0 else ""
    return f"{sign}{value * 100:.{decimals}f}%"


def _get_color(value: float) -> str:
    """Get color based on positive/negative value."""
    if value > 0:
        return "green"
    elif value < 0:
        return "red"
    return "white"


class ConsoleFormatter:
    """Rich console formatter for portfolio data."""

    def __init__(self, console: Console | None = None):
        if not RICH_AVAILABLE:
            raise ImportError("Rich library required. Install with: pip install rich")
        self.console = console or Console()

    def print_portfolio(self, portfolio: Portfolio) -> None:
        """Print portfolio summary."""
        # Summary panel
        summary_text = Text()
        summary_text.append(f"Net Assets: ${float(portfolio.net_assets):,.2f}\n", style="bold")
        summary_text.append(f"Cash: ${float(portfolio.cash):,.2f}\n")
        summary_text.append(f"Market Value: ${float(portfolio.market_value):,.2f}\n")

        day_pnl = float(portfolio.day_pnl)
        color = _get_color(day_pnl)
        summary_text.append("Day P&L: ", style="")
        summary_text.append(
            f"{_format_money(day_pnl)} ({_format_pct(portfolio.day_pnl_pct)})", style=color
        )

        self.console.print(Panel(summary_text, title="Portfolio Summary", border_style="blue"))

        # Holdings table
        table = Table(title="Holdings")
        table.add_column("Ticker", style="cyan", no_wrap=True)
        table.add_column("Weight", justify="right")
        table.add_column("Shares", justify="right")
        table.add_column("Price", justify="right")
        table.add_column("Value", justify="right")
        table.add_column("Day P&L", justify="right")
        table.add_column("Total P&L", justify="right")

        equity_positions = [p for p in portfolio.sorted_by_weight if not p.is_option]
        option_positions = [p for p in portfolio.sorted_by_weight if p.is_option]

        for pos in equity_positions[:15]:
            day_color = _get_color(float(pos.day_pnl))
            total_color = _get_color(float(pos.unrealized_pnl))

            table.add_row(
                pos.symbol.ticker,
                f"{pos.weight * 100:.1f}%",
                f"{float(pos.quantity):,.0f}",
                f"${float(pos.current_price or 0):,.2f}",
                f"${float(pos.market_value):,.0f}",
                Text(_format_money(float(pos.day_pnl), 0), style=day_color),
                Text(_format_money(float(pos.unrealized_pnl), 0), style=total_color),
            )

        self.console.print(table)

        # Option positions in a separate table
        if option_positions:
            opt_table = Table(title="Option Positions")
            opt_table.add_column("Contract", style="magenta", no_wrap=True)
            opt_table.add_column("Qty", justify="right")
            opt_table.add_column("Avg Cost", justify="right")
            opt_table.add_column("Price", justify="right")
            opt_table.add_column("Value", justify="right")
            opt_table.add_column("P&L", justify="right")

            for pos in option_positions:
                pnl_color = _get_color(float(pos.unrealized_pnl))
                opt_table.add_row(
                    pos.symbol.ticker,
                    f"{float(pos.quantity):,.0f}",
                    f"${float(pos.avg_cost or 0):,.2f}",
                    f"${float(pos.current_price or 0):,.2f}",
                    f"${float(pos.market_value):,.0f}",
                    Text(_format_money(float(pos.unrealized_pnl), 0), style=pnl_color),
                )

            self.console.print(opt_table)

    def print_risk_metrics(self, metrics: RiskMetrics) -> None:
        """Print risk metrics."""
        table = Table(title="Risk Metrics")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", justify="right")

        if metrics.volatility_annualized is not None:
            table.add_row("Volatility (Ann.)", f"{metrics.volatility_annualized * 100:.1f}%")

        if metrics.garch_vol_forecast is not None:
            table.add_row("GARCH Vol Forecast", f"{metrics.garch_vol_forecast * 100:.1f}%")

        if metrics.beta_spy is not None:
            table.add_row("Beta (SPY)", f"{metrics.beta_spy:.2f}")

        if metrics.beta_qqq is not None:
            table.add_row("Beta (QQQ)", f"{metrics.beta_qqq:.2f}")

        if metrics.sharpe_ratio is not None:
            table.add_row("Sharpe Ratio", f"{metrics.sharpe_ratio:.2f}")

        if metrics.var_95 is not None:
            var_text = f"{metrics.var_95 * 100:.2f}%"
            if metrics.var_95_amount:
                var_text += f" (${float(metrics.var_95_amount):,.0f})"
            table.add_row("VaR 95%", var_text)

        if metrics.max_drawdown is not None:
            table.add_row("Max Drawdown", f"{metrics.max_drawdown * 100:.1f}%")

        if metrics.hhi is not None:
            table.add_row("HHI (Concentration)", f"{metrics.hhi:.3f}")

        self.console.print(table)

        if metrics.high_corr_pairs:
            corr_table = Table(title="High Correlations")
            corr_table.add_column("Pair")
            corr_table.add_column("Correlation", justify="right")

            for t1, t2, corr in metrics.high_corr_pairs[:5]:
                corr_table.add_row(f"{t1} - {t2}", f"{corr:.2f}")

            self.console.print(corr_table)

    def print_history(self, snapshots: list[PortfolioSnapshot]) -> None:
        """Print portfolio snapshot history."""
        if not snapshots:
            self.console.print("[yellow]No snapshot history available.[/yellow]")
            return

        table = Table(title="Portfolio History")
        table.add_column("Timestamp", style="cyan")
        table.add_column("Net Assets", justify="right")
        table.add_column("Cash", justify="right")
        table.add_column("Market Value", justify="right")
        table.add_column("Day P&L", justify="right")

        for snap in snapshots:
            day_pnl = snap.day_pnl or 0
            color = _get_color(day_pnl)
            table.add_row(
                snap.timestamp.strftime("%Y-%m-%d %H:%M"),
                f"${snap.net_assets:,.2f}",
                f"${snap.cash:,.2f}",
                f"${snap.market_value:,.2f}",
                Text(_format_money(day_pnl, 0), style=color),
            )

        self.console.print(table)

    def print_performance(self, metrics: PerformanceMetrics) -> None:
        """Print performance metrics."""
        text = Text()
        period = "N/A"
        if metrics.first_date and metrics.last_date:
            period = f"{metrics.first_date:%Y-%m-%d} → {metrics.last_date:%Y-%m-%d}"
        text.append(f"Period: {period}\n")
        text.append(f"Snapshots: {metrics.total_snapshots}\n")
        text.append(f"Starting NAV: ${metrics.starting_nav:,.2f}\n")
        text.append(f"Ending NAV: ${metrics.ending_nav:,.2f}\n")

        ret_color = _get_color(metrics.total_return_pct)
        text.append("Return: ")
        text.append(f"{metrics.total_return_pct * 100:+.2f}%\n", style=ret_color)

        text.append(f"Max Drawdown: {metrics.max_drawdown_pct * 100:.2f}%\n", style="red")
        text.append(f"Avg Daily P&L: ${metrics.avg_daily_pnl:,.2f}\n")
        text.append(f"Best Day: ${metrics.best_day_pnl:,.2f}\n", style="green")
        text.append(f"Worst Day: ${metrics.worst_day_pnl:,.2f}\n", style="red")

        total_days = metrics.positive_days + metrics.negative_days
        win_rate = (metrics.positive_days / total_days * 100) if total_days else 0
        text.append(f"Win Rate: {win_rate:.0f}% ({metrics.positive_days}W / {metrics.negative_days}L)")

        self.console.print(Panel(text, title="Performance Metrics", border_style="blue"))

    def print_rebalance(self, actions: list[RebalanceAction]) -> None:
        """Print rebalance actions."""
        if not actions:
            self.console.print("[green]Portfolio is on target. No rebalancing needed.[/green]")
            return

        table = Table(title="Rebalance Actions")
        table.add_column("Ticker", style="cyan", no_wrap=True)
        table.add_column("Current %", justify="right")
        table.add_column("Target %", justify="right")
        table.add_column("Deviation", justify="right")
        table.add_column("Status", justify="center")
        table.add_column("$ Amount", justify="right")
        table.add_column("Shares", justify="right")

        for a in actions:
            dev_color = _get_color(-abs(a.deviation)) if a.status != "ON_TARGET" else "white"
            status_style = {
                "OVERWEIGHT": "red",
                "UNDERWEIGHT": "yellow",
                "ON_TARGET": "green",
                "BUY": "cyan",
            }.get(a.status, "white")

            table.add_row(
                a.ticker,
                f"{a.current_weight * 100:.1f}%",
                f"{a.target_weight * 100:.1f}%",
                Text(f"{a.deviation * 100:+.1f}%", style=dev_color),
                Text(a.status, style=status_style),
                _format_money(a.dollar_amount, 0),
                str(a.shares),
            )

        self.console.print(table)

    def print_alerts(self, alerts: list[Alert]) -> None:
        """Print alerts."""
        if not alerts:
            self.console.print("[green]No alerts[/green]")
            return

        for alert in alerts:
            style = {
                "info": "blue",
                "warning": "yellow",
                "critical": "red bold",
            }.get(alert.severity.value, "white")

            self.console.print(
                Panel(
                    f"{alert.message}",
                    title=alert.title,
                    border_style=style,
                )
            )


# Convenience functions for simple usage
def print_portfolio(portfolio: Portfolio) -> None:
    """Print portfolio summary to console."""
    if RICH_AVAILABLE:
        formatter = ConsoleFormatter()
        formatter.print_portfolio(portfolio)
    else:
        _print_portfolio_plain(portfolio)


def print_risk_metrics(metrics: RiskMetrics) -> None:
    """Print risk metrics to console."""
    if RICH_AVAILABLE:
        formatter = ConsoleFormatter()
        formatter.print_risk_metrics(metrics)
    else:
        _print_risk_plain(metrics)


def _print_portfolio_plain(portfolio: Portfolio) -> None:
    """Plain text fallback for portfolio."""
    print("\n=== Portfolio Summary ===")
    print(f"Net Assets: ${float(portfolio.net_assets):,.2f}")
    print(f"Cash: ${float(portfolio.cash):,.2f}")
    print(f"Day P&L: {_format_money(float(portfolio.day_pnl))}")

    equities = [p for p in portfolio.sorted_by_weight if not p.is_option]
    options = [p for p in portfolio.sorted_by_weight if p.is_option]

    print("\nTop Holdings:")
    for pos in equities[:10]:
        print(f"  {pos.symbol.ticker}: {pos.weight * 100:.1f}% | ${float(pos.market_value):,.0f}")

    if options:
        print("\nOption Positions:")
        for pos in options:
            print(
                f"  {pos.symbol.ticker}: qty={float(pos.quantity):.0f} "
                f"| ${float(pos.market_value):,.0f}"
            )


def _print_risk_plain(metrics: RiskMetrics) -> None:
    """Plain text fallback for risk metrics."""
    print("\n=== Risk Metrics ===")
    if metrics.volatility_annualized:
        print(f"Volatility: {metrics.volatility_annualized * 100:.1f}%")
    if metrics.beta_spy:
        print(f"Beta (SPY): {metrics.beta_spy:.2f}")
    if metrics.sharpe_ratio:
        print(f"Sharpe Ratio: {metrics.sharpe_ratio:.2f}")
