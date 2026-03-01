"""Overview page: portfolio summary, holdings table, weight pie chart."""

from __future__ import annotations

from typing import TYPE_CHECKING

import streamlit as st

if TYPE_CHECKING:
    from clawdfolio.core.types import Portfolio


def _get_portfolio() -> Portfolio:
    """Get portfolio using demo broker as fallback."""
    from clawdfolio.brokers import get_broker
    from clawdfolio.brokers.demo import DemoBroker  # noqa: F401

    try:
        from clawdfolio.brokers.aggregator import aggregate_portfolios
        from clawdfolio.core.config import load_config

        config = load_config()
        brokers = []
        for name, bcfg in config.brokers.items():
            if not bcfg.enabled or name == "demo":
                continue
            try:
                brokers.append(get_broker(name, bcfg))
            except KeyError:
                pass
        if brokers:
            return aggregate_portfolios(brokers)
    except Exception:
        pass

    broker = get_broker("demo")
    broker.connect()
    return broker.get_portfolio()


def render() -> None:
    """Render the overview page."""
    import plotly.express as px

    st.header("Portfolio Overview")

    try:
        portfolio = _get_portfolio()
    except Exception as e:
        st.error(f"Failed to load portfolio: {e}")
        return

    # Summary cards
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Net Assets", f"${float(portfolio.net_assets):,.0f}")
    col2.metric("Market Value", f"${float(portfolio.market_value):,.0f}")
    col3.metric("Cash", f"${float(portfolio.cash):,.0f}")

    day_pnl = float(portfolio.day_pnl)
    col4.metric(
        "Day P&L",
        f"${day_pnl:,.0f}",
        delta=f"{portfolio.day_pnl_pct*100:+.2f}%",
    )

    # Holdings table
    st.subheader("Holdings")
    rows = []
    for pos in portfolio.sorted_by_weight:
        rows.append({
            "Ticker": pos.symbol.ticker,
            "Weight": f"{pos.weight*100:.1f}%",
            "Shares": float(pos.quantity),
            "Price": float(pos.current_price or 0),
            "Value": float(pos.market_value),
            "Day P&L": float(pos.day_pnl),
        })
    st.dataframe(rows, use_container_width=True)

    # Pie chart
    st.subheader("Allocation")
    labels = [pos.symbol.ticker for pos in portfolio.sorted_by_weight[:10]]
    values = [pos.weight for pos in portfolio.sorted_by_weight[:10]]
    fig = px.pie(names=labels, values=values, hole=0.4)
    fig.update_layout(margin={"t": 0, "b": 0, "l": 0, "r": 0})
    st.plotly_chart(fig, use_container_width=True)
