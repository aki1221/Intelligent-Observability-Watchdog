"""
Unit tests for the System State API endpoint.
"""

import pytest


class TestSystemState:
    """Tests for GET /api/v1/state/"""

    def test_get_state_empty(self, client):
        response = client.get("/api/v1/state/")
        assert response.status_code == 200
        data = response.json()
        assert data["total_events"] == 0
        assert data["events_last_hour"] == 0
        assert data["active_alerts"] == 0
        assert data["active_rules"] == 0
        assert "severity_breakdown" in data
        assert data["severity_breakdown"]["info"] == 0
        assert data["severity_breakdown"]["error"] == 0

    def test_get_state_with_events(self, client):
        # Ingest some events
        for i in range(5):
            client.post("/api/v1/events/", json={
                "source": "svc",
                "event_type": "test",
                "message": f"Event {i}",
                "severity": "error",
            })

        response = client.get("/api/v1/state/")
        data = response.json()
        assert data["total_events"] == 5
        assert data["events_last_hour"] == 5
        assert data["severity_breakdown"]["error"] == 5

    def test_get_state_with_rules(self, client):
        client.post("/api/v1/alerts/rules", json={
            "name": "Rule 1", "event_type": "x", "condition": "c", "enabled": True,
        })
        client.post("/api/v1/alerts/rules", json={
            "name": "Rule 2", "event_type": "x", "condition": "c", "enabled": False,
        })

        response = client.get("/api/v1/state/")
        data = response.json()
        assert data["active_rules"] == 1  # only enabled ones


class TestHealthEndpoints:
    """Tests for health check endpoints."""

    def test_root(self, client):
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "service" in data

    def test_health(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
