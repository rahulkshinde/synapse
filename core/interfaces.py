"""Abstract Base Classes (ABCs) for provider plugins.

This module defines the interfaces that all provider implementations must follow,
enabling a plugin-first architecture where new providers can be added without
modifying core application logic.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class MetricsProvider(ABC):
    """Abstract base class for metrics data providers.
    
    Implementations should connect to various monitoring systems (Prometheus,
    Datadog, CloudWatch, etc.) and provide a unified interface for querying metrics.
    """

    @abstractmethod
    def get_metrics(
        self, query: str, start_time: Optional[str] = None, end_time: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Retrieve metrics based on a query.
        
        Args:
            query: Query string or metric name to retrieve
            start_time: Optional start time for time-range queries (ISO 8601 format)
            end_time: Optional end time for time-range queries (ISO 8601 format)
            
        Returns:
            List of metric data points, each as a dictionary with keys like:
            - timestamp: ISO 8601 timestamp
            - value: Numeric metric value
            - labels: Dictionary of label key-value pairs
        """
        pass

    @abstractmethod
    def list_available_metrics(self) -> List[str]:
        """List all available metric names from this provider.
        
        Returns:
            List of metric name strings
        """
        pass

    @abstractmethod
    def health_check(self) -> bool:
        """Check if the metrics provider is healthy and reachable.
        
        Returns:
            True if provider is healthy, False otherwise
        """
        pass


class KnowledgeProvider(ABC):
    """Abstract base class for knowledge base providers.
    
    Implementations should connect to various knowledge sources (documentation,
    runbooks, wikis, etc.) and provide a unified interface for retrieving
    contextual information.
    """

    @abstractmethod
    def search(
        self, query: str, limit: int = 10, filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Search the knowledge base for relevant information.
        
        Args:
            query: Search query string
            limit: Maximum number of results to return
            filters: Optional dictionary of filters (e.g., {"category": "incident"})
            
        Returns:
            List of knowledge items, each as a dictionary with keys like:
            - title: Title of the knowledge item
            - content: Full text content
            - source: Source identifier (URL, file path, etc.)
            - relevance_score: Optional relevance score (0.0 to 1.0)
        """
        pass

    @abstractmethod
    def get_by_id(self, item_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a specific knowledge item by its identifier.
        
        Args:
            item_id: Unique identifier for the knowledge item
            
        Returns:
            Dictionary containing the knowledge item, or None if not found
        """
        pass

    @abstractmethod
    def health_check(self) -> bool:
        """Check if the knowledge provider is healthy and reachable.
        
        Returns:
            True if provider is healthy, False otherwise
        """
        pass


class CommunicationProvider(ABC):
    """Abstract base class for communication channel providers.
    
    Implementations should connect to various communication platforms (Slack,
    PagerDuty, email, etc.) and provide a unified interface for sending
    notifications and alerts.
    """

    @abstractmethod
    def send_message(
        self,
        channel: str,
        message: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Send a message to a communication channel.
        
        Args:
            channel: Channel identifier (e.g., Slack channel name, email address)
            message: Message content to send
            metadata: Optional dictionary of additional metadata (priority, tags, etc.)
            
        Returns:
            Dictionary with response information, including:
            - message_id: Unique identifier for the sent message
            - status: Delivery status ("sent", "failed", etc.)
            - timestamp: ISO 8601 timestamp of when message was sent
        """
        pass

    @abstractmethod
    def send_alert(
        self,
        severity: str,
        title: str,
        description: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Send an alert/incident notification.
        
        Args:
            severity: Alert severity level (e.g., "critical", "warning", "info")
            title: Alert title
            description: Detailed alert description
            metadata: Optional dictionary of additional metadata (incident_id, links, etc.)
            
        Returns:
            Dictionary with response information, including:
            - alert_id: Unique identifier for the alert
            - status: Delivery status
            - timestamp: ISO 8601 timestamp
        """
        pass

    @abstractmethod
    def health_check(self) -> bool:
        """Check if the communication provider is healthy and reachable.
        
        Returns:
            True if provider is healthy, False otherwise
        """
        pass
