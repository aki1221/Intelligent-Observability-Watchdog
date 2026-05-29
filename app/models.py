import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Boolean, Enum as SAEnum
from app.database import Base
import enum


class EventSeverity(str, enum.Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertStatus(str, enum.Enum):
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    source = Column(String(255), nullable=False, index=True)
    event_type = Column(String(255), nullable=False, index=True)
    severity = Column(SAEnum(EventSeverity), default=EventSeverity.INFO, index=True)
    message = Column(Text, nullable=False)
    metadata_json = Column(Text, default="{}")  # JSON string for flexible metadata
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class AlertRule(Base):
    __tablename__ = "alert_rules"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True)
    description = Column(Text, default="")
    event_type = Column(String(255), nullable=False)
    severity_threshold = Column(SAEnum(EventSeverity), default=EventSeverity.ERROR)
    condition = Column(Text, nullable=False)  # e.g., "count > 5 in 5m"
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    rule_id = Column(Integer, nullable=False, index=True)
    status = Column(SAEnum(AlertStatus), default=AlertStatus.ACTIVE, index=True)
    message = Column(Text, nullable=False)
    triggered_at = Column(DateTime, default=datetime.datetime.utcnow)
    acknowledged_at = Column(DateTime, nullable=True)
    resolved_at = Column(DateTime, nullable=True)


class HealthSnapshot(Base):
    __tablename__ = "health_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    total_events_1h = Column(Integer, default=0)
    error_count_1h = Column(Integer, default=0)
    critical_count_1h = Column(Integer, default=0)
    active_alerts = Column(Integer, default=0)
    breaches = Column(Integer, default=0)


class WebhookLog(Base):
    __tablename__ = "webhook_logs"

    id = Column(Integer, primary_key=True, index=True)
    alert_id = Column(Integer, nullable=False)
    rule_name = Column(String(255), nullable=False)
    status_code = Column(Integer, default=200)
    delivered = Column(Boolean, default=True)
    response_body = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
