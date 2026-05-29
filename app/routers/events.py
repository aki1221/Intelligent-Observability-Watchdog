import datetime
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.database import get_db
from app.models import Event, EventSeverity
from app.schemas import EventCreate, EventResponse
from app.websocket import manager

router = APIRouter(prefix="/api/v1/events", tags=["Events"])


async def _broadcast_event(event_data: dict):
    """Background task to broadcast event via WebSocket."""
    await manager.broadcast({"type": "new_event", "data": event_data})


@router.post("/", response_model=EventResponse, status_code=201)
async def ingest_event(
    event: EventCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Ingest a new observability event."""
    db_event = Event(
        source=event.source,
        event_type=event.event_type,
        severity=event.severity,
        message=event.message,
        metadata_json=event.metadata_json,
        timestamp=datetime.datetime.utcnow(),
    )
    db.add(db_event)
    db.commit()
    db.refresh(db_event)

    # Broadcast to WebSocket clients
    background_tasks.add_task(
        _broadcast_event,
        {
            "id": db_event.id,
            "source": db_event.source,
            "event_type": db_event.event_type,
            "severity": db_event.severity.value,
            "message": db_event.message,
            "timestamp": str(db_event.timestamp),
        },
    )
    return db_event


@router.post("/batch", response_model=list[EventResponse], status_code=201)
async def ingest_events_batch(
    events: list[EventCreate],
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Ingest multiple events in a single request."""
    db_events = []
    for event in events:
        db_event = Event(
            source=event.source,
            event_type=event.event_type,
            severity=event.severity,
            message=event.message,
            metadata_json=event.metadata_json,
            timestamp=datetime.datetime.utcnow(),
        )
        db.add(db_event)
        db_events.append(db_event)
    db.commit()
    for e in db_events:
        db.refresh(e)

    # Broadcast batch to WebSocket clients
    for db_event in db_events:
        background_tasks.add_task(
            _broadcast_event,
            {
                "id": db_event.id,
                "source": db_event.source,
                "event_type": db_event.event_type,
                "severity": db_event.severity.value,
                "message": db_event.message,
                "timestamp": str(db_event.timestamp),
            },
        )
    return db_events


@router.get("/", response_model=list[EventResponse])
def query_events(
    source: Optional[str] = Query(None),
    event_type: Optional[str] = Query(None),
    severity: Optional[EventSeverity] = Query(None),
    start_time: Optional[datetime.datetime] = Query(None),
    end_time: Optional[datetime.datetime] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """Query events with optional filters."""
    query = db.query(Event)

    if source:
        query = query.filter(Event.source == source)
    if event_type:
        query = query.filter(Event.event_type == event_type)
    if severity:
        query = query.filter(Event.severity == severity)
    if start_time:
        query = query.filter(Event.timestamp >= start_time)
    if end_time:
        query = query.filter(Event.timestamp <= end_time)

    query = query.order_by(desc(Event.timestamp))
    return query.offset(offset).limit(limit).all()


@router.get("/{event_id}", response_model=EventResponse)
def get_event(event_id: int, db: Session = Depends(get_db)):
    """Get a single event by ID."""
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event
