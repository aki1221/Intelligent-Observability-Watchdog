"""
Unit tests for the Events API endpoints.
"""

import pytest


class TestEventIngestion:
    """Tests for POST /api/v1/events/"""

    def test_ingest_single_event(self, client):
        payload = {
            "source": "test-service",
            "event_type": "http_error",
            "severity": "error",
            "message": "Test error occurred",
            "metadata_json": '{"code": 500}',
        }
        response = client.post("/api/v1/events/", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["source"] == "test-service"
        assert data["event_type"] == "http_error"
        assert data["severity"] == "error"
        assert data["message"] == "Test error occurred"
        assert data["id"] is not None
        assert data["timestamp"] is not None

    def test_ingest_event_default_severity(self, client):
        payload = {
            "source": "test-service",
            "event_type": "deployment",
            "message": "Deployed v1.0",
        }
        response = client.post("/api/v1/events/", json=payload)
        assert response.status_code == 201
        assert response.json()["severity"] == "info"

    def test_ingest_event_missing_required_fields(self, client):
        # Missing 'message'
        payload = {"source": "test-service", "event_type": "error"}
        response = client.post("/api/v1/events/", json=payload)
        assert response.status_code == 422

    def test_ingest_event_empty_source(self, client):
        payload = {"source": "", "event_type": "error", "message": "fail"}
        response = client.post("/api/v1/events/", json=payload)
        assert response.status_code == 422

    def test_ingest_event_invalid_severity(self, client):
        payload = {
            "source": "svc",
            "event_type": "error",
            "message": "fail",
            "severity": "catastrophic",
        }
        response = client.post("/api/v1/events/", json=payload)
        assert response.status_code == 422


class TestEventBatchIngestion:
    """Tests for POST /api/v1/events/batch"""

    def test_ingest_batch(self, client):
        events = [
            {"source": "svc-a", "event_type": "error", "message": "Error 1", "severity": "error"},
            {"source": "svc-b", "event_type": "info", "message": "Info 1", "severity": "info"},
            {"source": "svc-c", "event_type": "warning", "message": "Warn 1", "severity": "warning"},
        ]
        response = client.post("/api/v1/events/batch", json=events)
        assert response.status_code == 201
        data = response.json()
        assert len(data) == 3
        assert data[0]["source"] == "svc-a"
        assert data[2]["severity"] == "warning"

    def test_ingest_empty_batch(self, client):
        response = client.post("/api/v1/events/batch", json=[])
        assert response.status_code == 201
        assert response.json() == []


class TestEventQuery:
    """Tests for GET /api/v1/events/"""

    def test_query_events_empty(self, client):
        response = client.get("/api/v1/events/")
        assert response.status_code == 200
        assert response.json() == []

    def test_query_events_after_ingestion(self, client):
        # Ingest some events
        for i in range(5):
            client.post("/api/v1/events/", json={
                "source": "svc",
                "event_type": "test",
                "message": f"Event {i}",
            })
        response = client.get("/api/v1/events/")
        assert response.status_code == 200
        assert len(response.json()) == 5

    def test_query_events_filter_by_source(self, client):
        client.post("/api/v1/events/", json={"source": "alpha", "event_type": "x", "message": "m1"})
        client.post("/api/v1/events/", json={"source": "beta", "event_type": "x", "message": "m2"})

        response = client.get("/api/v1/events/", params={"source": "alpha"})
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["source"] == "alpha"

    def test_query_events_filter_by_severity(self, client):
        client.post("/api/v1/events/", json={"source": "s", "event_type": "e", "message": "m", "severity": "critical"})
        client.post("/api/v1/events/", json={"source": "s", "event_type": "e", "message": "m", "severity": "info"})

        response = client.get("/api/v1/events/", params={"severity": "critical"})
        data = response.json()
        assert len(data) == 1
        assert data[0]["severity"] == "critical"

    def test_query_events_pagination(self, client):
        for i in range(10):
            client.post("/api/v1/events/", json={"source": "s", "event_type": "e", "message": f"m{i}"})

        response = client.get("/api/v1/events/", params={"limit": 3, "offset": 0})
        assert len(response.json()) == 3

        response = client.get("/api/v1/events/", params={"limit": 3, "offset": 9})
        assert len(response.json()) == 1


class TestEventGetById:
    """Tests for GET /api/v1/events/{event_id}"""

    def test_get_event_by_id(self, client):
        resp = client.post("/api/v1/events/", json={"source": "s", "event_type": "e", "message": "m"})
        event_id = resp.json()["id"]

        response = client.get(f"/api/v1/events/{event_id}")
        assert response.status_code == 200
        assert response.json()["id"] == event_id

    def test_get_event_not_found(self, client):
        response = client.get("/api/v1/events/9999")
        assert response.status_code == 404
