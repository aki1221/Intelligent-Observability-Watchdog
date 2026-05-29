"""
Unit tests for the Alerts API endpoints (rules + triggered alerts).
"""

import pytest


# ─── Alert Rules ─────────────────────────────────────────────────────────────

class TestAlertRuleCreate:
    """Tests for POST /api/v1/alerts/rules"""

    def test_create_rule(self, client):
        payload = {
            "name": "Test Rule",
            "event_type": "http_error",
            "condition": "count > 5 in 5m",
            "severity_threshold": "error",
            "description": "A test rule",
            "enabled": True,
        }
        response = client.post("/api/v1/alerts/rules", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Rule"
        assert data["event_type"] == "http_error"
        assert data["condition"] == "count > 5 in 5m"
        assert data["enabled"] is True
        assert data["id"] is not None

    def test_create_rule_minimal(self, client):
        payload = {
            "name": "Minimal Rule",
            "event_type": "cpu_spike",
            "condition": "count > 3 in 2m",
        }
        response = client.post("/api/v1/alerts/rules", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["severity_threshold"] == "error"  # default
        assert data["enabled"] is True  # default

    def test_create_rule_duplicate_name(self, client):
        payload = {"name": "Unique Rule", "event_type": "x", "condition": "count > 1 in 1m"}
        client.post("/api/v1/alerts/rules", json=payload)
        response = client.post("/api/v1/alerts/rules", json=payload)
        assert response.status_code == 409

    def test_create_rule_missing_fields(self, client):
        payload = {"name": "Incomplete"}
        response = client.post("/api/v1/alerts/rules", json=payload)
        assert response.status_code == 422


class TestAlertRuleList:
    """Tests for GET /api/v1/alerts/rules"""

    def test_list_rules_empty(self, client):
        response = client.get("/api/v1/alerts/rules")
        assert response.status_code == 200
        assert response.json() == []

    def test_list_rules(self, client):
        for i in range(3):
            client.post("/api/v1/alerts/rules", json={
                "name": f"Rule {i}",
                "event_type": "test",
                "condition": "count > 1 in 1m",
            })
        response = client.get("/api/v1/alerts/rules")
        assert len(response.json()) == 3

    def test_list_rules_filter_enabled(self, client):
        client.post("/api/v1/alerts/rules", json={
            "name": "Enabled", "event_type": "x", "condition": "c", "enabled": True,
        })
        client.post("/api/v1/alerts/rules", json={
            "name": "Disabled", "event_type": "x", "condition": "c", "enabled": False,
        })
        response = client.get("/api/v1/alerts/rules", params={"enabled": True})
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Enabled"


class TestAlertRuleGetUpdateDelete:
    """Tests for GET/PATCH/DELETE /api/v1/alerts/rules/{rule_id}"""

    def _create_rule(self, client):
        resp = client.post("/api/v1/alerts/rules", json={
            "name": "Updatable Rule",
            "event_type": "test",
            "condition": "count > 1 in 1m",
        })
        return resp.json()["id"]

    def test_get_rule(self, client):
        rule_id = self._create_rule(client)
        response = client.get(f"/api/v1/alerts/rules/{rule_id}")
        assert response.status_code == 200
        assert response.json()["id"] == rule_id

    def test_get_rule_not_found(self, client):
        response = client.get("/api/v1/alerts/rules/9999")
        assert response.status_code == 404

    def test_update_rule(self, client):
        rule_id = self._create_rule(client)
        response = client.patch(f"/api/v1/alerts/rules/{rule_id}", json={
            "enabled": False,
            "condition": "count > 10 in 10m",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["enabled"] is False
        assert data["condition"] == "count > 10 in 10m"

    def test_update_rule_not_found(self, client):
        response = client.patch("/api/v1/alerts/rules/9999", json={"enabled": False})
        assert response.status_code == 404

    def test_delete_rule(self, client):
        rule_id = self._create_rule(client)
        response = client.delete(f"/api/v1/alerts/rules/{rule_id}")
        assert response.status_code == 204

        # Verify deleted
        response = client.get(f"/api/v1/alerts/rules/{rule_id}")
        assert response.status_code == 404

    def test_delete_rule_not_found(self, client):
        response = client.delete("/api/v1/alerts/rules/9999")
        assert response.status_code == 404


# ─── Triggered Alerts ────────────────────────────────────────────────────────

class TestAlertsList:
    """Tests for GET /api/v1/alerts/"""

    def test_list_alerts_empty(self, client):
        response = client.get("/api/v1/alerts/")
        assert response.status_code == 200
        assert response.json() == []


class TestAlertStatusUpdate:
    """Tests for PATCH /api/v1/alerts/{alert_id}/status"""

    def _create_alert(self, client, db_session):
        """Helper: create a rule then manually insert an alert."""
        from app.models import Alert, AlertRule, AlertStatus
        import datetime

        rule = AlertRule(
            name="Test Rule for Alert",
            event_type="test",
            condition="count > 1 in 1m",
            enabled=True,
        )
        db_session.add(rule)
        db_session.commit()
        db_session.refresh(rule)

        alert = Alert(
            rule_id=rule.id,
            status=AlertStatus.ACTIVE,
            message="Test alert triggered",
            triggered_at=datetime.datetime.utcnow(),
        )
        db_session.add(alert)
        db_session.commit()
        db_session.refresh(alert)
        return alert.id

    def test_acknowledge_alert(self, client, db_session):
        alert_id = self._create_alert(client, db_session)
        response = client.patch(f"/api/v1/alerts/{alert_id}/status", json={"status": "acknowledged"})
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "acknowledged"
        assert data["acknowledged_at"] is not None

    def test_resolve_alert(self, client, db_session):
        alert_id = self._create_alert(client, db_session)
        response = client.patch(f"/api/v1/alerts/{alert_id}/status", json={"status": "resolved"})
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "resolved"
        assert data["resolved_at"] is not None

    def test_update_alert_not_found(self, client):
        response = client.patch("/api/v1/alerts/9999/status", json={"status": "acknowledged"})
        assert response.status_code == 404

    def test_update_alert_invalid_status(self, client, db_session):
        alert_id = self._create_alert(client, db_session)
        response = client.patch(f"/api/v1/alerts/{alert_id}/status", json={"status": "invalid"})
        assert response.status_code == 422
