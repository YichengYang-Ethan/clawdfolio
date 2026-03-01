"""Format alerts and data for Telegram messages."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..core.types import Alert


def format_alert_telegram(alert: Alert) -> str:
    """Format an Alert into a Telegram-friendly markdown string."""
    icon = {
        "info": "ℹ️",
        "warning": "⚠️",
        "critical": "🚨",
    }.get(alert.severity.value, "")

    lines = [f"{icon} *{_escape_md(alert.title)}*"]

    if alert.message:
        lines.append(_escape_md(alert.message))

    return "\n".join(lines)


def format_alerts_telegram(alerts: list[Alert]) -> str:
    """Format multiple alerts into a single Telegram message."""
    if not alerts:
        return "✅ No alerts"

    parts = [format_alert_telegram(a) for a in alerts]
    return "\n\n".join(parts)


def _escape_md(text: str) -> str:
    """Escape special characters for Telegram MarkdownV2.

    Only escapes characters that Telegram requires escaping in
    non-entity positions.
    """
    chars = r"_[]()~`>#+-=|{}.!"
    out: list[str] = []
    for ch in text:
        if ch in chars:
            out.append("\\")
        out.append(ch)
    return "".join(out)
