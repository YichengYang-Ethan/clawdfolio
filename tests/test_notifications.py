"""Tests for notification modules."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from clawdfolio.notifications import send_notification
from clawdfolio.notifications.email import send_email
from clawdfolio.notifications.telegram import send_telegram


class TestSendNotificationDispatch:
    """Tests for send_notification dispatcher."""

    @patch("clawdfolio.notifications.telegram.send_telegram")
    def test_dispatch_telegram(self, mock_send):
        config = {"bot_token": "123:ABC", "chat_id": "456"}
        send_notification("telegram", config, "hello")
        mock_send.assert_called_once_with(bot_token="123:ABC", chat_id="456", message="hello")

    @patch("clawdfolio.notifications.email.send_email")
    def test_dispatch_email(self, mock_send):
        config = {
            "smtp_host": "smtp.example.com",
            "smtp_port": "465",
            "username": "user@example.com",
            "password": "secret",
            "to": "recipient@example.com",
            "subject": "Test Subject",
        }
        send_notification("email", config, "body text")
        mock_send.assert_called_once_with(
            smtp_host="smtp.example.com",
            smtp_port=465,
            username="user@example.com",
            password="secret",
            to_addr="recipient@example.com",
            subject="Test Subject",
            body="body text",
        )

    @patch("clawdfolio.notifications.email.send_email")
    def test_dispatch_email_default_port_and_subject(self, mock_send):
        config = {
            "smtp_host": "smtp.example.com",
            "username": "user@example.com",
            "password": "secret",
            "to": "recipient@example.com",
        }
        send_notification("email", config, "body")
        mock_send.assert_called_once()
        call_kwargs = mock_send.call_args
        assert call_kwargs[1]["smtp_port"] == 587
        assert call_kwargs[1]["subject"] == "Clawdfolio Alert"

    def test_dispatch_unknown_method(self):
        with pytest.raises(ValueError, match="Unknown notification method"):
            send_notification("sms", {}, "hello")


class TestSendTelegram:
    """Tests for send_telegram function."""

    @patch("urllib.request.urlopen")
    def test_send_success(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        send_telegram("123:TOKEN", "chat123", "Test message")

        mock_urlopen.assert_called_once()
        req = mock_urlopen.call_args[0][0]
        assert "123:TOKEN" in req.full_url
        body = json.loads(req.data.decode("utf-8"))
        assert body["chat_id"] == "chat123"
        assert body["text"] == "Test message"
        assert body["parse_mode"] == "HTML"

    @patch("urllib.request.urlopen")
    def test_send_api_error(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.status = 403
        mock_resp.read.return_value = b'{"ok":false}'
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        with pytest.raises(RuntimeError, match="Telegram API error 403"):
            send_telegram("bad_token", "chat", "msg")

    @patch("urllib.request.urlopen", side_effect=ConnectionError("timeout"))
    def test_send_network_error(self, mock_urlopen):
        with pytest.raises(ConnectionError, match="timeout"):
            send_telegram("tok", "chat", "msg")


class TestSendEmail:
    """Tests for send_email function."""

    @patch("smtplib.SMTP")
    def test_send_success(self, mock_smtp_cls):
        mock_server = MagicMock()
        mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=mock_server)
        mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)

        send_email(
            smtp_host="smtp.example.com",
            smtp_port=587,
            username="user@test.com",
            password="pass",
            to_addr="to@test.com",
            subject="Subj",
            body="Body text",
        )

        mock_server.ehlo.assert_called()
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with("user@test.com", "pass")
        mock_server.sendmail.assert_called_once()
        args = mock_server.sendmail.call_args[0]
        assert args[0] == "user@test.com"
        assert args[1] == ["to@test.com"]

    @patch("smtplib.SMTP", side_effect=ConnectionRefusedError("refused"))
    def test_send_connection_error(self, mock_smtp_cls):
        with pytest.raises(ConnectionRefusedError):
            send_email("host", 587, "u", "p", "to@x.com", "sub", "body")
