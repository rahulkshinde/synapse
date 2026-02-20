"""Provider factory for loading and managing provider instances.

This module implements a Factory Pattern to dynamically load provider plugins
based on environment configuration, enabling a plugin-first architecture.
"""

import logging
import os
from typing import Dict, List, Optional, Type

from .interfaces import CommunicationProvider, KnowledgeProvider, MetricsProvider

logger = logging.getLogger(__name__)


class ProviderFactory:
    """Factory for creating and managing provider instances.
    
    Loads provider implementations based on environment variables and provides
    a centralized registry for accessing providers throughout the application.
    """

    def __init__(self):
        """Initialize the provider factory."""
        self._metrics_providers: Dict[str, MetricsProvider] = {}
        self._knowledge_providers: Dict[str, KnowledgeProvider] = {}
        self._communication_providers: Dict[str, CommunicationProvider] = {}
        self._load_providers()

    def _load_providers(self):
        """Load provider instances from environment configuration."""
        # Load metrics providers
        metrics_config = os.getenv("METRICS_PROVIDERS", "").strip()
        if metrics_config:
            for provider_name in metrics_config.split(","):
                provider_name = provider_name.strip()
                if provider_name:
                    self._load_metrics_provider(provider_name)

        # Load knowledge providers
        knowledge_config = os.getenv("KNOWLEDGE_PROVIDERS", "").strip()
        if knowledge_config:
            for provider_name in knowledge_config.split(","):
                provider_name = provider_name.strip()
                if provider_name:
                    self._load_knowledge_provider(provider_name)

        # Load communication providers
        communication_config = os.getenv("COMMUNICATION_PROVIDERS", "").strip()
        if communication_config:
            for provider_name in communication_config.split(","):
                provider_name = provider_name.strip()
                if provider_name:
                    self._load_communication_provider(provider_name)

    def _load_metrics_provider(self, provider_name: str):
        """Load a metrics provider by name.
        
        Args:
            provider_name: Name of the provider (e.g., "prometheus")
        """
        try:
            if provider_name.lower() == "prometheus":
                from providers.metrics.prometheus import PrometheusMetricsProvider

                base_url = os.getenv("PROMETHEUS_URL", "http://localhost:9090")
                provider = PrometheusMetricsProvider(base_url=base_url)
                self._metrics_providers["prometheus"] = provider
                logger.info(f"Loaded metrics provider: {provider_name}")
            else:
                logger.warning(f"Unknown metrics provider: {provider_name}")
        except Exception as e:
            logger.error(f"Failed to load metrics provider {provider_name}: {str(e)}", exc_info=True)

    def _load_knowledge_provider(self, provider_name: str):
        """Load a knowledge provider by name.
        
        Args:
            provider_name: Name of the provider
        """
        try:
            # TODO: Add knowledge provider implementations
            logger.warning(f"Knowledge provider {provider_name} not yet implemented")
        except Exception as e:
            logger.error(f"Failed to load knowledge provider {provider_name}: {str(e)}", exc_info=True)

    def _load_communication_provider(self, provider_name: str):
        """Load a communication provider by name.
        
        Args:
            provider_name: Name of the provider (e.g., "slack")
        """
        try:
            if provider_name.lower() == "slack":
                from providers.communication.slack import SlackCommunicationProvider

                bot_token = os.getenv("SLACK_BOT_TOKEN")
                if not bot_token:
                    raise ValueError("SLACK_BOT_TOKEN environment variable is required")

                default_channel = os.getenv("SLACK_DEFAULT_CHANNEL", "#incidents")
                provider = SlackCommunicationProvider(
                    bot_token=bot_token, default_channel=default_channel
                )
                self._communication_providers["slack"] = provider
                logger.info(f"Loaded communication provider: {provider_name}")
            else:
                logger.warning(f"Unknown communication provider: {provider_name}")
        except Exception as e:
            logger.error(f"Failed to load communication provider {provider_name}: {str(e)}", exc_info=True)

    def get_metrics_provider(self, name: Optional[str] = None) -> Optional[MetricsProvider]:
        """Get a metrics provider by name, or return the first available.
        
        Args:
            name: Optional provider name. If None, returns the first available provider.
            
        Returns:
            MetricsProvider instance or None if not found
        """
        if name:
            return self._metrics_providers.get(name.lower())
        elif self._metrics_providers:
            return next(iter(self._metrics_providers.values()))
        return None

    def get_knowledge_provider(self, name: Optional[str] = None) -> Optional[KnowledgeProvider]:
        """Get a knowledge provider by name, or return the first available.
        
        Args:
            name: Optional provider name. If None, returns the first available provider.
            
        Returns:
            KnowledgeProvider instance or None if not found
        """
        if name:
            return self._knowledge_providers.get(name.lower())
        elif self._knowledge_providers:
            return next(iter(self._knowledge_providers.values()))
        return None

    def get_communication_provider(
        self, name: Optional[str] = None
    ) -> Optional[CommunicationProvider]:
        """Get a communication provider by name, or return the first available.
        
        Args:
            name: Optional provider name. If None, returns the first available provider.
            
        Returns:
            CommunicationProvider instance or None if not found
        """
        if name:
            return self._communication_providers.get(name.lower())
        elif self._communication_providers:
            return next(iter(self._communication_providers.values()))
        return None

    def list_metrics_providers(self) -> List[str]:
        """List all loaded metrics provider names.
        
        Returns:
            List of provider names
        """
        return list(self._metrics_providers.keys())

    def list_knowledge_providers(self) -> List[str]:
        """List all loaded knowledge provider names.
        
        Returns:
            List of provider names
        """
        return list(self._knowledge_providers.keys())

    def list_communication_providers(self) -> List[str]:
        """List all loaded communication provider names.
        
        Returns:
            List of provider names
        """
        return list(self._communication_providers.keys())


# Global factory instance
_factory: Optional[ProviderFactory] = None


def get_factory() -> ProviderFactory:
    """Get the global provider factory instance.
    
    Returns:
        ProviderFactory instance
    """
    global _factory
    if _factory is None:
        _factory = ProviderFactory()
    return _factory
