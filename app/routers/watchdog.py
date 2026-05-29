"""
Watchdog router — trigger evaluations, view health snapshots and webhook logs.
"""

import datetime
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.database import get_db
from app.models import (
    Event, Alert, AlertRule, AlertStatus, EventSeverity,
    HealthSnapshot, WebhookLog,
)
from app.watchdog import run_watchdog_cycle

router = APIRouter(prefix="/api/v1/watchdog", tags=["Watchdog"])


@router.post("/run")
def trigger_watchdog(db: Session = Depends(get_db)):
    """Manually trigger a watchdog evaluation cycle."""
    breaches = run_watchdog_cycle()

    # Record a health snapshot
    now = datetime.datetime.utcnow()
    one_hour_ago = now - datetime.timedelta(hours=1)

    total_events_1h = (
        db.query(func.count(Event.id))
        .filter(Event.timestamp >= one_hour_ago)
        .scalar() or 0
    )
    error_count_1h = (
        db.query(func.count(Event.id))
        .filter(Event.timestamp >= one_hour_ago, Event.severity == EventSeverity.ERROR)
        .scalar() or 0
    )
    critical_count_1h = (
        db.query(func.count(Event.id))
        .filter(Event.timestamp >= one_hour_ago, Event.severity == EventSeverity.CRITICAL)
        .scalar() or 0
    )
    active_alerts = (
        db.query(func.count(Alert.id))
        .filter(Alert.status == AlertStatus.ACTIVE)
        .scalar() or 0
    )

    snapshot = HealthSnapshot(
        timestamp=now,
        total_events_1h=total_events_1h,
        error_count_1h=error_count_1h,
        critical_count_1h=critical_count_1h,
        active_alerts=active_alerts,
        breaches=len(breaches),
    )
    db.add(snapshot)

    # Log simulated webhook deliveries for each breach
    for breach in breaches:
        log = WebhookLog(
            alert_id=0,  # simplified
            rule_name=breach["rule_name"],
            status_code=200,
            delivered=True,
            response_body="Webhook delivered (simulated)",
            created_at=now,
        )
        db.add(log)

    db.commit()

    return {
        "breaches_detected": len(breaches),
        "breaches": breaches,
        "snapshot_recorded": True,
    }


@router.get("/health-snapshots")
def get_health_snapshots(
    hours: int = Query(24, ge=1, le=168),
    db: Session = Depends(get_db),
):
    """Get health snapshots for the specified time range."""
    since = datetime.datetime.utcnow() - datetime.timedelta(hours=hours)
    snapshots = (
        db.query(HealthSnapshot)
        .filter(HealthSnapshot.timestamp >= since)
        .order_by(HealthSnapshot.timestamp)
        .all()
    )
    return [
        {
            "id": s.id,
            "timestamp": s.timestamp.isoformat(),
            "total_events_1h": s.total_events_1h,
            "error_count_1h": s.error_count_1h,
            "critical_count_1h": s.critical_count_1h,
            "active_alerts": s.active_alerts,
            "breaches": s.breaches,
        }
        for s in snapshots
    ]


@router.get("/webhook-logs")
def get_webhook_logs(
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """Get recent webhook delivery logs."""
    logs = (
        db.query(WebhookLog)
        .order_by(desc(WebhookLog.created_at))
        .limit(limit)
        .all()
    )
    return [
        {
            "id": l.id,
            "alert_id": l.alert_id,
            "rule_name": l.rule_name,
            "status_code": l.status_code,
            "delivered": l.delivered,
            "response_body": l.response_body,
            "created_at": l.created_at.isoformat(),
        }
        for l in logs
    ]
