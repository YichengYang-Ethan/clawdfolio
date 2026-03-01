"""Tests for v3 config additions (notifications, rebalancing)."""

from clawdfolio.core.config import Config, NotificationConfig, RebalanceTarget, RebalancingConfig


class TestNotificationConfig:
    """Tests for NotificationConfig."""

    def test_defaults(self):
        """Test default notification config."""
        cfg = NotificationConfig()
        assert cfg.enabled is False
        assert cfg.gateway_url == "http://localhost:18789"
        assert cfg.timeout == 10

    def test_from_dict(self):
        """Test parsing notification config from dict."""
        data = {
            "notifications": {
                "enabled": True,
                "gateway_url": "http://localhost:9999",
                "timeout": 30,
            }
        }
        config = Config.from_dict(data)
        assert config.notifications.enabled is True
        assert config.notifications.gateway_url == "http://localhost:9999"
        assert config.notifications.timeout == 30

    def test_from_dict_missing(self):
        """Test missing notification config uses defaults."""
        config = Config.from_dict({})
        assert config.notifications.enabled is False

    def test_to_dict_roundtrip(self):
        """Test notification config survives to_dict/from_dict roundtrip."""
        config = Config.from_dict({
            "notifications": {"enabled": True, "gateway_url": "http://test:1234"},
        })
        data = config.to_dict()
        config2 = Config.from_dict(data)
        assert config2.notifications.enabled is True
        assert config2.notifications.gateway_url == "http://test:1234"


class TestRebalancingConfig:
    """Tests for RebalancingConfig."""

    def test_defaults(self):
        """Test default rebalancing config."""
        cfg = RebalancingConfig()
        assert cfg.tolerance == 0.03
        assert cfg.targets == []

    def test_from_dict(self):
        """Test parsing rebalancing config from dict."""
        data = {
            "rebalancing": {
                "tolerance": 0.05,
                "targets": [
                    {"ticker": "QQQ", "weight": 0.30},
                    {"ticker": "VOO", "weight": 0.25},
                ],
            }
        }
        config = Config.from_dict(data)
        assert config.rebalancing.tolerance == 0.05
        assert len(config.rebalancing.targets) == 2
        assert config.rebalancing.targets[0].ticker == "QQQ"
        assert config.rebalancing.targets[0].weight == 0.30

    def test_from_dict_invalid_target_skipped(self):
        """Test invalid target entries are skipped."""
        data = {
            "rebalancing": {
                "targets": [
                    {"ticker": "QQQ", "weight": 0.30},
                    {"only_ticker": "BAD"},  # Missing weight
                    "not_a_dict",
                ],
            }
        }
        config = Config.from_dict(data)
        assert len(config.rebalancing.targets) == 1

    def test_to_dict_roundtrip(self):
        """Test rebalancing config survives roundtrip."""
        data = {
            "rebalancing": {
                "tolerance": 0.05,
                "targets": [{"ticker": "SPY", "weight": 0.40}],
            }
        }
        config = Config.from_dict(data)
        data2 = config.to_dict()
        config2 = Config.from_dict(data2)
        assert config2.rebalancing.tolerance == 0.05
        assert config2.rebalancing.targets[0].ticker == "SPY"

    def test_rebalance_target_dataclass(self):
        """Test RebalanceTarget dataclass."""
        t = RebalanceTarget(ticker="AAPL", weight=0.25)
        assert t.ticker == "AAPL"
        assert t.weight == 0.25
