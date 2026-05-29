import datetime
from typing import Optional
from pydantic import BaseModel, Field

from app.models import EventSeverity, AlertStatus


# ─── Event Schemas ───────────────────────────────────────────────────────────

class EventCreate(BaseModel):
    source: str = Field(..., min_length=1, max_length=255, examples=["payment-service"])
    event_type: str = Field(..., min_length=1, max_length=255, examples=["error"])
    severity: EventSeverity = EventSeverity.INFO
    message: str = Field(..., min_length=1, examples=["Connection timeout to DB"])
    metadata_json: Optional[str] = Field(default="{}", examples=['{"host": "db-01"}'])


class EventResponse(BaseModel):
    id: int
    source: str
    event_type: str
    severity: EventSeverity
    message: str
    metadata_json: Optional[str]
    timestamp: datetime.datetime
    created_at: datetime.datetime

    class Config:
        from_attributes = True


class EventQuery(BaseModel):
    source: Optional[str] = None
    event_type: Optional[str] = None
    severity: Optional[EventSeverity] = None
    start_time: Optional[datetime.datetime] = None
    end_time: Optional[datetime.datetime] = None
    limit: int = Field(default=100, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)


# ─── Alert Rule Schemas ──────────────────────────────────────────────────────

class AlertRuleCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, examples=["High Error Rate"])
    description: Optional[str] = ""
    event_type: str = Field(..., min_length=1, max_length=255, examples=["error"])
    severity_threshold: EventSeverity = EventSeverity.ERROR
    condition: str = Field(..., min_length=1, examples=["count > 5 in 5m"])
    enabled: bool = True


class AlertRuleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    event_type: Optional[str] = None
    severity_threshold: Optional[EventSeverity] = None
    condition: Optional[str] = None
    enabled: Optional[bool] = None


class AlertRuleResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    event_type: str
    severity_threshold: EventSeverity
    condition: str
    enabled: bool
    created_at: datetime.datetime
    updated_at: datetime.datetime

    class Config:
        from_attributes = True


# ─── Alert Schemas ───────────────────────────────────────────────────────────

class AlertResponse(BaseModel):
    id: int
    rule_id: int
    status: AlertStatus
    message: str
    triggered_at: datetime.datetime
    acknowledged_at: Optional[datetime.datetime]
    resolved_at: Optional[datetime.datetime]

    class Config:
        from_attributes = True


class AlertStatusUpdate(BaseModel):
    status: AlertStatus


# ─── System State ────────────────────────────────────────────────────────────

class SystemState(BaseModel):
    total_events: int
    events_last_hour: int
    active_alerts: int
    active_rules: int
    severity_breakdown: dict
