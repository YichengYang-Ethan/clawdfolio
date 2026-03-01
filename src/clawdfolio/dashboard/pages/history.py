"""History page: NAV line chart and daily P&L bar chart."""

from __future__ import annotations

import streamlit as st


def render() -> None:
    """Render the history page."""
    import plotly.express as px

    from clawdfolio.storage.repository import get_performance, get_snapshots

    st.header("Portfolio History")

    days = st.slider("Days to display", min_value=7, max_value=365, value=30)
    snapshots = get_snapshots(days=days)

    if not snapshots:
        st.info("No snapshots found. Run `clawdfolio history snapshot` to start tracking.")
        return

    dates = [s.timestamp for s in snapshots]
    navs = [s.net_assets for s in snapshots]
    pnls = [s.day_pnl for s in snapshots]

    # NAV line chart
    st.subheader("Net Asset Value")
    fig_nav = px.line(x=dates, y=navs, labels={"x": "Date", "y": "NAV ($)"})
    fig_nav.update_layout(margin={"t": 0, "b": 0})
    st.plotly_chart(fig_nav, use_container_width=True)

    # Daily P&L bar chart
    st.subheader("Daily P&L")
    colors = ["green" if p >= 0 else "red" for p in pnls]
    fig_pnl = px.bar(x=dates, y=pnls, labels={"x": "Date", "y": "P&L ($)"})
    fig_pnl.update_traces(marker_color=colors)
    fig_pnl.update_layout(margin={"t": 0, "b": 0})
    st.plotly_chart(fig_pnl, use_container_width=True)

    # Performance metrics
    metrics = get_performance(days=days)
    if metrics:
        st.subheader("Performance Summary")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Return", f"{metrics.total_return_pct*100:+.2f}%")
        col2.metric("Max Drawdown", f"{metrics.max_drawdown_pct*100:.2f}%")
        col3.metric("Avg Daily P&L", f"${metrics.avg_daily_pnl:,.0f}")
        col4.metric("Win/Loss", f"{metrics.positive_days}/{metrics.negative_days}")
