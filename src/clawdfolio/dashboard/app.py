"""Main Streamlit dashboard entry point."""

from __future__ import annotations

import streamlit as st

st.set_page_config(
    page_title="Clawdfolio Dashboard",
    page_icon="📊",
    layout="wide",
)

page = st.sidebar.radio(
    "Navigation",
    ["Overview", "Risk", "History", "Alerts", "Rebalance"],
)

if page == "Overview":
    from .pages.overview import render
    render()
elif page == "Risk":
    from .pages.risk import render
    render()
elif page == "History":
    from .pages.history import render
    render()
elif page == "Alerts":
    from .pages.alerts import render
    render()
elif page == "Rebalance":
    from .pages.rebalance import render
    render()
