from fastapi import Depends, FastAPI
from sqlalchemy import select
from sqlalchemy.orm import Session

from .db import get_session
from .embeddings import embed
from .gemini_client import assess
from .models import MissionLog
from .schemas import MissionAssessment, MissionLogEntry, RoverTelemetry

app = FastAPI(title="ARES-Twin Mission Control")


def _telemetry_to_text(t: RoverTelemetry) -> str:
    return (
        f"position=({t.x:.2f},{t.y:.2f},{t.z:.2f}) "
        f"battery={t.battery:.1f}% motor_torque={t.motor_torque:.2f}Nm"
    )


def _format_context(events: list[MissionLog]) -> str:
    return "\n".join(
        f"- {e.timestamp.isoformat()} {_telemetry_to_text_row(e)} "
        f"→ {e.status}: {e.recommended_action}"
        for e in events
    )


def _telemetry_to_text_row(e: MissionLog) -> str:
    return (
        f"position=({e.x:.2f},{e.y:.2f},{e.z:.2f}) "
        f"battery={e.battery:.1f}% motor_torque={e.motor_torque:.2f}Nm"
    )


@app.get("/")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "ares-twin-mission-control"}


@app.post("/telemetry", response_model=MissionAssessment)
def post_telemetry(
    telemetry: RoverTelemetry, db: Session = Depends(get_session)
) -> MissionAssessment:
    query_text = _telemetry_to_text(telemetry)
    query_embedding = embed(query_text)

    similar = db.scalars(
        select(MissionLog)
        .order_by(MissionLog.embedding.l2_distance(query_embedding))
        .limit(3)
    ).all()

    context = _format_context(similar) if similar else ""
    assessment = assess(telemetry, context=context)

    db.add(
        MissionLog(
            timestamp=telemetry.timestamp,
            x=telemetry.x,
            y=telemetry.y,
            z=telemetry.z,
            battery=telemetry.battery,
            motor_torque=telemetry.motor_torque,
            status=assessment.status,
            reasoning=assessment.reasoning,
            recommended_action=assessment.recommended_action,
            embedding=query_embedding,
        )
    )
    db.commit()

    return assessment


@app.get("/mission-log", response_model=list[MissionLogEntry])
def get_mission_log(
    limit: int = 20, db: Session = Depends(get_session)
) -> list[MissionLog]:
    return list(
        db.scalars(
            select(MissionLog).order_by(MissionLog.timestamp.desc()).limit(limit)
        ).all()
    )
