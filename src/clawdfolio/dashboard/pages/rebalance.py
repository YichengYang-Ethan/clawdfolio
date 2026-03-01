"""Rebalance page: deviation chart and action table."""

from __future__ import annotations

import streamlit as st


def render() -> None:
    """Render the rebalance page."""
    import plotly.express as px

    from clawdfolio.core.config import load_config
    from clawdfolio.strategies.rebalance import (
        TargetAllocation,
        calculate_rebalance,
        propose_dca_allocation,
    )

    st.header("Rebalance Analysis")

    config = load_config()
    if not config.rebalancing.targets:
        st.info("No rebalancing targets configured. Add 'rebalancing.targets' to your config.")
        return

    targets = [
        TargetAllocation(ticker=t.ticker, weight=t.weight)
        for t in config.rebalancing.targets
    ]

    try:
        from .overview import _get_portfolio

        portfolio = _get_portfolio()
    except Exception as e:
        st.error(f"Failed to load portfolio: {e}")
        return

    actions = calculate_rebalance(portfolio, targets, tolerance=config.rebalancing.tolerance)

    if not actions:
        st.success("Portfolio is balanced")
        return

    # Deviation bar chart
    st.subheader("Weight Deviation from Target")
    tickers = [a.ticker for a in actions]
    deviations = [a.deviation * 100 for a in actions]
    fig = px.bar(
        x=tickers,
        y=deviations,
        labels={"x": "Ticker", "y": "Deviation (%)"},
        color=["Overweight" if d > 0 else "Underweight" for d in deviations],
        color_discrete_map={"Overweight": "red", "Underweight": "green"},
    )
    fig.update_layout(margin={"t": 0, "b": 0})
    st.plotly_chart(fig, use_container_width=True)

    # Actions table
    st.subheader("Recommended Actions")
    rows = []
    for a in actions:
        action_text = ""
        if a.status == "OVERWEIGHT":
            action_text = f"Sell ${abs(a.dollar_amount):,.0f}"
        elif a.status == "UNDERWEIGHT":
            action_text = f"Buy ${a.dollar_amount:,.0f}"
        rows.append({
            "Status": a.status,
            "Ticker": a.ticker,
            "Current": f"{a.current_weight*100:.1f}%",
            "Target": f"{a.target_weight*100:.1f}%",
            "Deviation": f"{a.deviation*100:+.1f}%",
            "Action": action_text,
        })
    st.dataframe(rows, use_container_width=True)

    # DCA proposal
    st.subheader("DCA Proposal")
    amount = st.number_input("Amount to invest ($)", min_value=100, value=5000, step=500)
    if st.button("Calculate"):
        proposals = propose_dca_allocation(portfolio, targets, amount=float(amount))
        if proposals:
            prop_rows = []
            for p in proposals:
                prop_rows.append({
                    "Ticker": p.ticker,
                    "Amount": f"${p.dollar_amount:,.0f}",
                    "Shares": p.shares,
                })
            st.dataframe(prop_rows, use_container_width=True)
        else:
            st.info("No underweight positions to invest in")
