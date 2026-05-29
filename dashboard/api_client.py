"""
HTTP client for communicating with the FastAPI backend.
"""

import httpx
from typing import Optional

API_BASE = "http://localhost:8000/api/v1"
TIMEOUT = 10.0


def _get(endpoint: str, params: Optional[dict] = None) -> dict | list:
    """GET request to the API."""
    resp = httpx.get(f"{API_BASE}{endpoint}", params=params, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def _post(endpoint: str, json_data: dict) -> dict:
    """POST request to the API."""
    resp = httpx.post(f"{API_BASE}{endpoint}", json=json_data, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def _patch(endpoint: str, json_data: dict) -> dict:
    """PATCH request to the API."""
    resp = httpx.patch(f"{API_BASE}{endpoint}", json=json_data, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def _delete(endpoint: str) -> None:
    """DELETE request to the API."""
    resp = httpx.delete(f"{API_BASE}{endpoint}", timeout=TIMEOUT)
    resp.raise_for_status()


# ─── State ───────────────────────────────────────────────────────────────────

def get_system_state() -> dict:
    return _get("/state/")


# ─── Events ─────────────────────────────────────────────────────────────────

def get_events(
    source: Optional[str] = None,
    event_type: Optional[str] = None,
    severity: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> list:
    params = {"limit": limit, "offset": offset}
    if source:
        params["source"] = source
    if event_type:
        params["event_type"] = event_type
    if severity:
        params["severity"] = severity
    return _get("/events/", params=params)


# ─── Alerts ──────────────────────────────────────────────────────────────────

def get_alerts(status: Optional[str] = None, limit: int = 100) -> list:
    params = {"limit": limit}
    if status:
        params["status"] = status
    return _get("/alerts/", params=params)


def update_alert_status(alert_id: int, status: str) -> dict:
    return _patch(f"/alerts/{alert_id}/status", {"status": status})


# ─── Alert Rules ─────────────────────────────────────────────────────────────

def get_alert_rules(enabled: Optional[bool] = None) -> list:
    params = {}
    if enabled is not None:
        params["enabled"] = enabled
    return _get("/alerts/rules", params=params)


def create_alert_rule(rule_data: dict) -> dict:
    return _post("/alerts/rules", rule_data)


def update_alert_rule(rule_id: int, update_data: dict) -> dict:
    return _patch(f"/alerts/rules/{rule_id}", update_data)


def delete_alert_rule(rule_id: int) -> None:
    _delete(f"/alerts/rules/{rule_id}")
