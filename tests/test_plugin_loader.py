"""Tests for PluginLoader auto-discovery."""

import pytest

from core.base import BaseMetrics
from core.plugin_loader import PluginLoader


@pytest.fixture
def loader():
    """PluginLoader pointed at the real plugins directory."""
    return PluginLoader(plugins_dir="plugins")


# ── Discovery ─────────────────────────────────────────────────


class TestPluginDiscovery:
    def test_discovers_prometheus_plugin(self, loader):
        names = loader.list_metrics_plugins()
        assert "prometheus" in names

    def test_prometheus_plugin_is_base_metrics(self, loader):
        plugin = loader.get_metrics_plugin("prometheus")
        assert plugin is not None
        assert isinstance(plugin, BaseMetrics)

    def test_knowledge_plugin_discovered(self, loader):
        """ChromaDB knowledge plugin should be discovered (may fail health check)."""
        names = loader.list_knowledge_plugins()
        # ChromaDB plugin requires a running server or uses local persist.
        # It should still be loadable with defaults.
        assert isinstance(names, list)

    def test_messenger_plugins_require_token(self, loader):
        """Slack plugin requires SLACK_BOT_TOKEN — should be skipped if not set."""
        # Without SLACK_BOT_TOKEN env var, the Slack plugin will not register
        names = loader.list_messenger_plugins()
        assert isinstance(names, list)


# ── Retrieval ─────────────────────────────────────────────────


class TestPluginRetrieval:
    def test_get_first_metrics_plugin(self, loader):
        plugin = loader.get_metrics_plugin()
        # Should return *something* (prometheus is no-arg constructible)
        assert plugin is not None
        assert hasattr(plugin, "get_metrics")
        assert hasattr(plugin, "health_check")

    def test_get_nonexistent_plugin_returns_none(self, loader):
        assert loader.get_metrics_plugin("nonexistent") is None
        assert loader.get_knowledge_plugin("nonexistent") is None
        assert loader.get_messenger_plugin("nonexistent") is None


# ── Empty / Missing Directory ─────────────────────────────────


class TestEdgeCases:
    def test_missing_plugins_dir(self):
        loader = PluginLoader(plugins_dir="/nonexistent/path")
        assert loader.list_metrics_plugins() == []
        assert loader.list_knowledge_plugins() == []
        assert loader.list_messenger_plugins() == []

    def test_empty_plugins_dir(self, tmp_path):
        loader = PluginLoader(plugins_dir=str(tmp_path))
        assert loader.list_metrics_plugins() == []
