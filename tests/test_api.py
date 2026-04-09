"""Tests for Synapse FastAPI endpoints."""

import pytest
from fastapi.testclient import TestClient

from app import app


@pytest.fixture
def client():
    """Synchronous test client for the FastAPI app."""
    return TestClient(app)


# ── Health & Info Endpoints ───────────────────────────────────


class TestHealthEndpoints:
    def test_root_returns_info(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Synapse SRE Framework"
        assert data["status"] == "operational"
        assert data["architecture"] == "plugin-first"
        assert data["privacy"] == "private-first"

    def test_health_returns_status(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert "plugins" in data
        assert "metrics" in data["plugins"]
        assert "knowledge" in data["plugins"]
        assert "messenger" in data["plugins"]

    def test_plugins_endpoint(self, client):
        resp = client.get("/plugins")
        assert resp.status_code == 200
        data = resp.json()
        assert "metrics" in data
        assert "knowledge" in data
        assert "messenger" in data
        assert isinstance(data["metrics"], list)


# ── Incident Endpoint ─────────────────────────────────────────


class TestIncidentEndpoint:
    def test_incident_accepts_valid_payload(self, client):
        """The /incident endpoint should accept PagerDuty-style payloads.

        Note: This will likely fail at the orchestrator level (no Ollama),
        but should return 500, not 422 (validation error).
        """
        payload = {
            "event": "incident.triggered",
            "incident": {
                "id": "PD-TEST-1",
                "title": "Test Alert",
                "description": "CPU high",
                "severity": "high",
            },
        }
        resp = client.post("/incident", json=payload)
        # Should be 202 (processed) or 500 (Ollama not available), not 422
        assert resp.status_code in (202, 500)

    def test_incident_rejects_bad_payload(self, client):
        resp = client.post("/incident", json={"bad": "data"})
        assert resp.status_code == 422


# ── Incidents Endpoint ────────────────────────────────────────


class TestIncidentsEndpoint:
    def test_create_incident_validates_schema(self, client):
        payload = {
            "title": "Test Incident",
            "description": "Testing incident creation",
            "severity": "high",
        }
        resp = client.post("/incidents", json=payload)
        # 201 (created) or 500 (no Ollama) — not 422
        assert resp.status_code in (201, 500)

    def test_create_incident_rejects_missing_fields(self, client):
        resp = client.post("/incidents", json={"title": "No severity"})
        assert resp.status_code == 422

    def test_create_incident_rejects_invalid_severity(self, client):
        payload = {
            "title": "Bad Severity",
            "description": "Testing",
            "severity": "mega-critical",
        }
        resp = client.post("/incidents", json=payload)
        assert resp.status_code == 422


# ── Webhook Endpoint ──────────────────────────────────────────


class TestWebhookEndpoint:
    def test_webhook_accepts_valid_payload(self, client):
        payload = {
            "event_type": "alert.fired",
            "source": "prometheus",
            "data": {"alertname": "HighCPU", "severity": "critical"},
        }
        resp = client.post("/webhook", json=payload)
        assert resp.status_code in (202, 500)

    def test_webhook_rejects_missing_fields(self, client):
        resp = client.post("/webhook", json={"event_type": "test"})
        assert resp.status_code == 422
