"""Email notification sender using stdlib smtplib."""

from __future__ import annotations

import logging
import smtplib
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)


def send_email(
    smtp_host: str,
    smtp_port: int,
    username: str,
    password: str,
    to_addr: str,
    subject: str,
    body: str,
) -> None:
    """Send an email notification via SMTP with STARTTLS.

    Args:
        smtp_host: SMTP server hostname
        smtp_port: SMTP server port (typically 587 for STARTTLS)
        username: SMTP login username
        password: SMTP login password (app password recommended)
        to_addr: Recipient email address
        subject: Email subject line
        body: Plain-text email body
    """
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = username
    msg["To"] = to_addr

    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=15) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(username, password)
            server.sendmail(username, [to_addr], msg.as_string())
        logger.info("Email sent to %s via %s", to_addr, smtp_host)
    except Exception as exc:
        logger.error("Failed to send email: %s", exc)
        raise
