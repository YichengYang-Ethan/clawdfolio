"""Alerts page: current alerts list with severity coloring."""

from __future__ import annotations

import streamlit as st


def render() -> None:
    """Render the alerts page."""
    st.header("Alerts")

    try:
        from clawdfolio.core.config import load_config
        from clawdfolio.monitors.earnings import EarningsMonitor
        from clawdfolio.monitors.price import PriceMonitor

        from .overview import _get_portfolio

        portfolio = _get_portfolio()
        config = load_config()
        monitor = PriceMonitor.from_config(config)
        monitor.leveraged_etfs = config.leveraged_etfs

        all_alerts = []
        all_alerts.extend(monitor.check_portfolio(portfolio))
        all_alerts.extend(EarningsMonitor().check_portfolio(portfolio))
    except Exception as e:
        st.error(f"Failed to check alerts: {e}")
        return

    if not all_alerts:
        st.success("No active alerts")
        return

    for alert in all_alerts:
        color_map = {
            "info": "blue",
            "warning": "orange",
            "critical": "red",
        }
        icon_map = {
            "info": "ℹ️",
            "warning": "⚠️",
            "critical": "🚨",
        }
        severity = alert.severity.value
        icon = icon_map.get(severity, "")
        bg_color = color_map.get(severity, "gray")

        st.markdown(
            f"""<div style="border-left: 4px solid {bg_color}; padding: 10px; margin: 5px 0;">
            <strong>{icon} {alert.title}</strong><br>
            {alert.message}
            </div>""",
            unsafe_allow_html=True,
        )
