"""
Watchdog Engine — Evaluates alert rules against recent events and triggers alerts on breach.
"""

import re
import datetime
from sqlalchemy import func

from app.database import SessionLocal
from app.models import Event, AlertRule, Alert, AlertStatus


def parse_condition(condition: str) -> tuple[int, int]:
    """
    Parse a condition string like 'count > 10 in 5m'.
    Returns (threshold, window_minutes).
    """
    match = re.match(r"count\s*>\s*(\d+)\s+in\s+(\d+)m", condition.strip())
    if not match:
        raise ValueError(f"Cannot parse condition: {condition}")
    threshold = int(match.group(1))
    window_minutes = int(match.group(2))
    return threshold, window_minutes


def run_watchdog_cycle() -> list[dict]:
    """
    Evaluate all enabled alert rules against recent events.
    Creates Alert records for any breaches detected.
    Returns a list of breach details.
    """
    db = SessionLocal()
    breaches = []

    try:
        # Get all enabled rules
        rules = db.query(AlertRule).filter(AlertRule.enabled == True).all()

        now = datetime.datetime.utcnow()

        for rule in rules:
            try:
                threshold, window_minutes = parse_condition(rule.condition)
            except ValueError:
                continue

            window_start = now - datetime.timedelta(minutes=window_minutes)

            # Count events matching this rule's criteria within the time window
            event_count = (
                db.query(func.count(Event.id))
                .filter(
                    Event.event_type == rule.event_type,
                    Event.timestamp >= window_start,
                )
                .scalar()
                or 0
            )

            if event_count > threshold:
                # Breach detected — create an alert
                alert_message = (
                    f"BREACHED: Rule '{rule.name}' — "
                    f"{event_count} events of type '{rule.event_type}' "
                    f"in last {window_minutes}m (threshold: {threshold})"
                )

                alert = Alert(
                    rule_id=rule.id,
                    status=AlertStatus.ACTIVE,
                    message=alert_message,
                    triggered_at=now,
                )
                db.add(alert)

                breaches.append({
                    "rule_name": rule.name,
                    "event_type": rule.event_type,
                    "severity": rule.severity_threshold.value,
                    "threshold": threshold,
                    "actual_count": event_count,
                    "window_minutes": window_minutes,
                })

        db.commit()
    finally:
        db.close()

    return breaches
