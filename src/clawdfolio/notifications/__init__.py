"""Notification dispatching for clawdfolio alerts."""

from __future__ import annotations

from typing import Any


def send_notification(method: str, config: dict[str, Any], message: str) -> None:
    """Dispatch a notification via the requested method.

    Args:
        method: "telegram" or "email"
        config: Method-specific configuration dict
        message: The message body to send
    """
    if method == "telegram":
        from .telegram import send_telegram

        send_telegram(
            bot_token=config["bot_token"],
            chat_id=config["chat_id"],
            message=message,
        )
    elif method == "email":
        from .email import send_email

        send_email(
            smtp_host=config["smtp_host"],
            smtp_port=int(config.get("smtp_port", 587)),
            username=config["username"],
            password=config["password"],
            to_addr=config["to"],
            subject=config.get("subject", "Clawdfolio Alert"),
            body=message,
        )
    else:
        raise ValueError(f"Unknown notification method: {method}")
