import datetime
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.database import get_db
from app.models import Alert, AlertRule, AlertStatus
from app.schemas import (
    AlertRuleCreate,
    AlertRuleUpdate,
    AlertRuleResponse,
    AlertResponse,
    AlertStatusUpdate,
)

router = APIRouter(prefix="/api/v1/alerts", tags=["Alerts"])


# ─── Alert Rules ─────────────────────────────────────────────────────────────

@router.post("/rules", response_model=AlertRuleResponse, status_code=201)
def create_alert_rule(rule: AlertRuleCreate, db: Session = Depends(get_db)):
    """Create a new alert rule."""
    existing = db.query(AlertRule).filter(AlertRule.name == rule.name).first()
    if existing:
        raise HTTPException(status_code=409, detail="Rule with this name already exists")

    db_rule = AlertRule(
        name=rule.name,
        description=rule.description,
        event_type=rule.event_type,
        severity_threshold=rule.severity_threshold,
        condition=rule.condition,
        enabled=rule.enabled,
    )
    db.add(db_rule)
    db.commit()
    db.refresh(db_rule)
    return db_rule


@router.get("/rules", response_model=list[AlertRuleResponse])
def list_alert_rules(
    enabled: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
):
    """List all alert rules."""
    query = db.query(AlertRule)
    if enabled is not None:
        query = query.filter(AlertRule.enabled == enabled)
    return query.all()


@router.get("/rules/{rule_id}", response_model=AlertRuleResponse)
def get_alert_rule(rule_id: int, db: Session = Depends(get_db)):
    """Get a single alert rule."""
    rule = db.query(AlertRule).filter(AlertRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Alert rule not found")
    return rule


@router.patch("/rules/{rule_id}", response_model=AlertRuleResponse)
def update_alert_rule(rule_id: int, update: AlertRuleUpdate, db: Session = Depends(get_db)):
    """Update an alert rule."""
    rule = db.query(AlertRule).filter(AlertRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Alert rule not found")

    update_data = update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(rule, field, value)

    rule.updated_at = datetime.datetime.utcnow()
    db.commit()
    db.refresh(rule)
    return rule


@router.delete("/rules/{rule_id}", status_code=204)
def delete_alert_rule(rule_id: int, db: Session = Depends(get_db)):
    """Delete an alert rule."""
    rule = db.query(AlertRule).filter(AlertRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Alert rule not found")
    db.delete(rule)
    db.commit()


# ─── Alerts (triggered instances) ────────────────────────────────────────────

@router.get("/", response_model=list[AlertResponse])
def list_alerts(
    status: Optional[AlertStatus] = Query(None),
    rule_id: Optional[int] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """List triggered alerts with optional filters."""
    query = db.query(Alert)
    if status:
        query = query.filter(Alert.status == status)
    if rule_id:
        query = query.filter(Alert.rule_id == rule_id)
    query = query.order_by(desc(Alert.triggered_at))
    return query.offset(offset).limit(limit).all()


@router.get("/{alert_id}", response_model=AlertResponse)
def get_alert(alert_id: int, db: Session = Depends(get_db)):
    """Get a single alert."""
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert


@router.patch("/{alert_id}/status", response_model=AlertResponse)
def update_alert_status(alert_id: int, update: AlertStatusUpdate, db: Session = Depends(get_db)):
    """Update alert status (acknowledge or resolve)."""
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert.status = update.status
    if update.status == AlertStatus.ACKNOWLEDGED:
        alert.acknowledged_at = datetime.datetime.utcnow()
    elif update.status == AlertStatus.RESOLVED:
        alert.resolved_at = datetime.datetime.utcnow()

    db.commit()
    db.refresh(alert)
    return alert
