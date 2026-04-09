"""Pydantic models for API request/response validation."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class Severity(str, Enum):

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class IncidentStatus(str, Enum):

    OPEN = "open"
    INVESTIGATING = "investigating"
    RESOLVED = "resolved"
    CLOSED = "closed"


class Metric(BaseModel):

    name: str = Field(..., description="Metric name/identifier")
    value: float = Field(..., description="Numeric metric value")
    timestamp: datetime = Field(..., description="ISO 8601 timestamp of the metric")
    labels: Dict[str, str] = Field(
        default_factory=dict, description="Key-value labels for the metric"
    )
    unit: Optional[str] = Field(None, description="Unit of measurement (e.g., 'bytes', 'seconds')")

    @field_validator("timestamp", mode="before")
    @classmethod
    def parse_timestamp(cls, v: Any) -> datetime:
        if isinstance(v, str):
            return datetime.fromisoformat(v.replace("Z", "+00:00"))
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "name": "cpu_usage_percent",
                "value": 85.5,
                "timestamp": "2026-02-20T12:00:00Z",
                "labels": {"host": "web-server-01", "environment": "production"},
                "unit": "percent",
            }
        }


class MetricQuery(BaseModel):

    query: str = Field(..., description="Metric query string or name")
    start_time: Optional[datetime] = Field(None, description="Start time for time-range queries")
    end_time: Optional[datetime] = Field(None, description="End time for time-range queries")
    provider: Optional[str] = Field(None, description="Specific metrics provider to use")

    @field_validator("start_time", "end_time", mode="before")
    @classmethod
    def parse_datetime(cls, v: Any) -> Optional[datetime]:
        if v is None or isinstance(v, datetime):
            return v
        if isinstance(v, str):
            return datetime.fromisoformat(v.replace("Z", "+00:00"))
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "query": "cpu_usage_percent",
                "start_time": "2026-02-20T10:00:00Z",
                "end_time": "2026-02-20T12:00:00Z",
                "provider": "prometheus",
            }
        }


class Incident(BaseModel):

    id: Optional[str] = Field(None, description="Unique incident identifier")
    title: str = Field(..., min_length=1, description="Incident title")
    description: str = Field(..., description="Detailed incident description")
    severity: Severity = Field(..., description="Incident severity level")
    status: IncidentStatus = Field(
        default=IncidentStatus.OPEN, description="Current incident status"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="ISO 8601 timestamp when incident was created"
    )
    updated_at: Optional[datetime] = Field(
        None, description="ISO 8601 timestamp when incident was last updated"
    )
    resolved_at: Optional[datetime] = Field(
        None, description="ISO 8601 timestamp when incident was resolved"
    )
    affected_services: List[str] = Field(
        default_factory=list, description="List of affected service names"
    )
    metrics: List[Metric] = Field(
        default_factory=list, description="Related metrics associated with the incident"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata as key-value pairs"
    )

    @field_validator("created_at", "updated_at", "resolved_at", mode="before")
    @classmethod
    def parse_datetime(cls, v: Any) -> Optional[datetime]:
        if v is None or isinstance(v, datetime):
            return v
        if isinstance(v, str):
            return datetime.fromisoformat(v.replace("Z", "+00:00"))
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "id": "inc-2026-001",
                "title": "High CPU Usage on Web Servers",
                "description": "CPU usage has exceeded 90% on multiple web servers",
                "severity": "high",
                "status": "investigating",
                "created_at": "2026-02-20T12:00:00Z",
                "affected_services": ["web-api", "frontend"],
                "metrics": [],
                "metadata": {"alert_source": "prometheus"},
            }
        }


class WebhookPayload(BaseModel):

    event_type: str = Field(..., description="Type of event (e.g., 'incident.created', 'alert.fired')")
    source: str = Field(..., description="Source system identifier")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="ISO 8601 timestamp of the event"
    )
    data: Dict[str, Any] = Field(..., description="Event-specific data payload")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata about the event"
    )

    @field_validator("timestamp", mode="before")
    @classmethod
    def parse_timestamp(cls, v: Any) -> datetime:
        if isinstance(v, str):
            return datetime.fromisoformat(v.replace("Z", "+00:00"))
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "event_type": "incident.created",
                "source": "pagerduty",
                "timestamp": "2026-02-20T12:00:00Z",
                "data": {
                    "incident_id": "inc-2026-001",
                    "title": "Service Degradation",
                    "severity": "high",
                },
                "metadata": {"webhook_id": "wh-12345"},
            }
        }


class PagerDutyWebhook(BaseModel):

    event: str = Field(..., description="Event type (e.g., 'incident.triggered', 'incident.acknowledged')")
    incident: Dict[str, Any] = Field(..., description="Incident data from PagerDuty")
    log_entries: Optional[List[Dict[str, Any]]] = Field(None, description="Log entries related to the incident")
    webhook: Optional[Dict[str, Any]] = Field(None, description="Webhook metadata")

    class Config:
        json_schema_extra = {
            "example": {
                "event": "incident.triggered",
                "incident": {
                    "id": "P123456",
                    "incident_number": 1,
                    "title": "High CPU Usage Alert",
                    "description": "CPU usage exceeded 90%",
                    "status": "triggered",
                    "severity": "high",
                    "urgency": "high",
                    "created_at": "2026-02-20T12:00:00Z",
                    "html_url": "https://example.pagerduty.com/incidents/P123456",
                    "service": {
                        "id": "S123456",
                        "name": "Web API Service",
                    },
                },
            }
        }
