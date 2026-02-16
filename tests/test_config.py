"""Tests for configuration loading."""

import yaml

from clawdfolio.core.config import Config, load_config


class TestConfig:
    def test_default_config(self):
        config = Config()
        assert config is not None

    def test_load_config_missing_file(self):
        """Loading a non-existent config file should return a valid config."""
        config = load_config("/nonexistent/path/config.yml")
        assert config is not None

    def test_load_config_from_yaml(self, tmp_path):
        config_file = tmp_path / "config.yml"
        config_file.write_text(yaml.dump({
            "brokers": {"demo": {"enabled": True}},
        }))
        config = load_config(str(config_file))
        assert config is not None
