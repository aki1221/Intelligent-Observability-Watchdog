from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import engine, Base
from app.routers import events, alerts, state
from app.websocket import manager

# Create all tables on startup
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.app_name,
    description="API-first Intelligent Observability & Event Watchdog",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS — allow all for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(events.router)
app.include_router(alerts.router)
app.include_router(state.router)


# ─── WebSocket Endpoint ──────────────────────────────────────────────────────

@app.websocket("/ws/events")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time event streaming."""
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive, listen for client messages (ping/pong)
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@app.get("/", tags=["Health"])
def root():
    return {"status": "ok", "service": settings.app_name}


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "healthy"}
