"""Plugin interfaces. Drop a .py file in /plugins that subclasses one of these."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class BaseMetrics(ABC):
    """Metrics plugin interface (Prometheus, CloudWatch, Datadog, etc.)."""

    @abstractmethod
    def get_metrics(
        self, query: str, start_time: Optional[str] = None, end_time: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def list_available_metrics(self) -> List[str]:
        pass

    @abstractmethod
    def health_check(self) -> bool:
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        pass


class BaseKnowledge(ABC):
    """Knowledge/RAG plugin interface (ChromaDB, Confluence, Markdown, etc.)."""

    @abstractmethod
    def search(
        self, query: str, limit: int = 10, filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def get_by_id(self, item_id: str) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    def health_check(self) -> bool:
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        pass


class BaseMessenger(ABC):
    """Messenger plugin interface (Slack, Teams, PagerDuty, etc.)."""

    @abstractmethod
    def send_message(
        self,
        channel: str,
        message: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        pass

    @abstractmethod
    def send_alert(
        self,
        severity: str,
        title: str,
        description: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        pass

    @abstractmethod
    def health_check(self) -> bool:
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        pass
