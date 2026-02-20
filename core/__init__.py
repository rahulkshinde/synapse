"""Core abstractions and interfaces for Synapse SRE Assistant."""

from .factory import ProviderFactory, get_factory
from .interfaces import (
    CommunicationProvider,
    KnowledgeProvider,
    MetricsProvider,
)
from .schemas import (
    Incident,
    Metric,
    MetricQuery,
    PagerDutyWebhook,
    WebhookPayload,
)

__all__ = [
    "MetricsProvider",
    "KnowledgeProvider",
    "CommunicationProvider",
    "Incident",
    "Metric",
    "MetricQuery",
    "WebhookPayload",
    "PagerDutyWebhook",
    "ProviderFactory",
    "get_factory",
]
