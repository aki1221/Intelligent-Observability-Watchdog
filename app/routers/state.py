import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models import Event, Alert, AlertRule, AlertStatus, EventSeverity
from app.schemas import SystemState

router = APIRouter(prefix="/api/v1/state", tags=["System State"])


@router.get("/", response_model=SystemState)
def get_system_state(db: Session = Depends(get_db)):
    """Get current system observability state summary."""
    total_events = db.query(func.count(Event.id)).scalar() or 0

    one_hour_ago = datetime.datetime.utcnow() - datetime.timedelta(hours=1)
    events_last_hour = (
        db.query(func.count(Event.id))
        .filter(Event.timestamp >= one_hour_ago)
        .scalar()
        or 0
    )

    active_alerts = (
        db.query(func.count(Alert.id))
        .filter(Alert.status == AlertStatus.ACTIVE)
        .scalar()
        or 0
    )

    active_rules = (
        db.query(func.count(AlertRule.id))
        .filter(AlertRule.enabled == True)
        .scalar()
        or 0
    )

    # Severity breakdown for last hour
    severity_counts = (
        db.query(Event.severity, func.count(Event.id))
        .filter(Event.timestamp >= one_hour_ago)
        .group_by(Event.severity)
        .all()
    )
    severity_breakdown = {s.value: 0 for s in EventSeverity}
    for sev, count in severity_counts:
        severity_breakdown[sev.value if hasattr(sev, "value") else sev] = count

    return SystemState(
        total_events=total_events,
        events_last_hour=events_last_hour,
        active_alerts=active_alerts,
        active_rules=active_rules,
        severity_breakdown=severity_breakdown,
    )
