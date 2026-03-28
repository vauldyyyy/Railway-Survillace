from collections.abc import Generator

from fastapi import Depends, FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.api.websockets import ConnectionManager
from app.core.database import Base, SessionLocal, engine
from app import models
from app.schemas import schemas

app = FastAPI(title="Railway Surveillance Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

manager = ConnectionManager()


@app.on_event("startup")
def create_tables() -> None:
    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/cameras", response_model=list[schemas.CameraResponse])
def list_cameras(db: Session = Depends(get_db)) -> list[models.Camera]:
    return db.query(models.Camera).all()


@app.post("/incidents", response_model=schemas.IncidentResponse)
def create_incident(
    payload: schemas.IncidentCreate,
    db: Session = Depends(get_db),
) -> models.Incident:
    incident = models.Incident(
        threat_type=payload.threat_type,
        camera_id=payload.camera_id,
    )
    db.add(incident)
    db.commit()
    db.refresh(incident)
    return incident


@app.get("/incidents", response_model=list[schemas.IncidentResponse])
def list_incidents(db: Session = Depends(get_db)) -> list[models.Incident]:
    return db.query(models.Incident).all()


@app.websocket("/ws/live_feed/{camera_id}")
async def live_feed(websocket: WebSocket, camera_id: str) -> None:
    await manager.connect(websocket)
    try:
        while True:
            message = await websocket.receive_text()
            await manager.broadcast(f"{camera_id}: {message}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
