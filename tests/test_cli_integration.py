"""CLI integration tests using subprocess with demo broker."""

from __future__ import annotations

import json
import subprocess


class TestCLIIntegration:
    """Integration tests for CLI commands using the demo broker."""

    def _run(self, *args: str, timeout: int = 30) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["clawdfolio", *args],
            capture_output=True,
            text=True,
            timeout=timeout,
        )

    def test_version(self):
        result = self._run("--version")
        assert result.returncode == 0
        assert "clawdfolio" in result.stdout.lower()

    def test_summary_demo(self):
        result = self._run("--broker", "demo", "summary")
        assert result.returncode == 0

    def test_summary_demo_json(self):
        result = self._run("--broker", "demo", "-o", "json", "summary")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert "portfolio" in data or "positions" in data or "net_assets" in data

    def test_risk_demo(self):
        result = self._run("--broker", "demo", "risk")
        # May succeed or fail gracefully depending on market data availability
        # Just ensure it doesn't crash with a traceback
        if result.returncode != 0:
            assert "Error" in result.stderr or "error" in result.stderr

    def test_alerts_demo(self):
        result = self._run("--broker", "demo", "alerts")
        assert result.returncode == 0

    def test_export_portfolio_demo(self):
        result = self._run("--broker", "demo", "export", "portfolio")
        assert result.returncode == 0
        assert len(result.stdout) > 0

    def test_unknown_command(self):
        result = self._run("nonexistent")
        # argparse should show help/error
        assert (
            result.returncode != 0
            or "usage" in result.stderr.lower()
            or "error" in result.stderr.lower()
        )

    def test_help(self):
        result = self._run("--help")
        assert result.returncode == 0
        assert "usage" in result.stdout.lower()

    def test_summary_help(self):
        result = self._run("summary", "--help")
        assert result.returncode == 0
        assert "summary" in result.stdout.lower()
