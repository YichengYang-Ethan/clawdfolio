"""Tests for CLI entry point."""

import subprocess
import sys


class TestCLI:
    def test_version_flag(self):
        result = subprocess.run(
            [sys.executable, "-c", "from clawdfolio.cli import main; main(['--version'])"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "clawdfolio" in result.stdout

    def test_help_flag(self):
        result = subprocess.run(
            [sys.executable, "-c", "from clawdfolio.cli import main; main(['--help'])"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "usage:" in result.stdout.lower() or "clawdfolio" in result.stdout.lower()

    def test_import(self):
        import clawdfolio

        assert hasattr(clawdfolio, "__version__")
        assert hasattr(clawdfolio, "Config")
        assert hasattr(clawdfolio, "Symbol")
        assert hasattr(clawdfolio, "Position")
        assert hasattr(clawdfolio, "Portfolio")
