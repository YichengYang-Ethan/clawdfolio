"""Telegram Bot API notification sender (stdlib only)."""

from __future__ import annotations

import json
import logging
import urllib.request

logger = logging.getLogger(__name__)

TELEGRAM_API_URL = "https://api.telegram.org/bot{token}/sendMessage"


def send_telegram(bot_token: str, chat_id: str, message: str) -> None:
    """Send a message via Telegram Bot API using urllib (no requests dependency).

    Args:
        bot_token: Telegram bot token (e.g. "123456:ABC-DEF...")
        chat_id: Target chat/channel ID
        message: Text message to send
    """
    url = TELEGRAM_API_URL.format(token=bot_token)
    payload = json.dumps({
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML",
    }).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status != 200:
                body = resp.read().decode("utf-8", errors="replace")
                logger.error("Telegram API returned %s: %s", resp.status, body)
                raise RuntimeError(f"Telegram API error {resp.status}: {body}")
    except Exception as exc:
        logger.error("Failed to send Telegram message: %s", exc)
        raise
