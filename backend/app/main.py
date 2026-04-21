from datetime import datetime, timezone
from pathlib import Path

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import nano_banana_client, veo_client
from .config import settings
from .db import SessionLocal, get_session
from .embeddings import embed
from .gemini_client import assess
from .models import MissionLog, MissionVideo, TerrainSnapshot
from .schemas import MissionAssessment, MissionLogEntry, RoverTelemetry

QUADRANT_SIZE_METERS = 10.0

app = FastAPI(title="ARES-Twin Mission Control")
app.mount("/media", StaticFiles(directory=settings.media_dir), name="media")


def _telemetry_to_text(t: RoverTelemetry) -> str:
    return (
        f"position=({t.x:.2f},{t.y:.2f},{t.z:.2f}) "
        f"battery={t.battery:.1f}% motor_torque={t.motor_torque:.2f}Nm"
    )


def _format_context(events: list[MissionLog]) -> str:
    return "\n".join(
        f"- {e.timestamp.isoformat()} "
        f"position=({e.x:.2f},{e.y:.2f},{e.z:.2f}) "
        f"battery={e.battery:.1f}% motor_torque={e.motor_torque:.2f}Nm "
        f"→ {e.status}: {e.recommended_action}"
        for e in events
    )


def _quadrant(x: float, y: float) -> tuple[int, int]:
    return int(x // QUADRANT_SIZE_METERS), int(y // QUADRANT_SIZE_METERS)


def _run_video_generation(video_id: int) -> None:
    db = SessionLocal()
    try:
        video = db.get(MissionVideo, video_id)
        if video is None:
            return
        try:
            relative_path = Path("videos") / f"{video_id:06d}.mp4"
            veo_client.generate(video.prompt, settings.media_dir / relative_path)
            video.status = "ready"
            video.video_path = str(relative_path)
            video.completed_at = datetime.now(timezone.utc)
        except Exception as exc:
            video.status = "failed"
            video.error = str(exc)
            video.completed_at = datetime.now(timezone.utc)
        db.commit()
    finally:
        db.close()


def _run_terrain_generation(snapshot_id: int) -> None:
    db = SessionLocal()
    try:
        snapshot = db.get(TerrainSnapshot, snapshot_id)
        if snapshot is None:
            return
        try:
            relative_path = (
                Path("terrain") / f"q_{snapshot.quadrant_x}_{snapshot.quadrant_y}.png"
            )
            nano_banana_client.generate(
                snapshot.prompt, settings.media_dir / relative_path
            )
            snapshot.status = "ready"
            snapshot.image_path = str(relative_path)
            snapshot.completed_at = datetime.now(timezone.utc)
        except Exception as exc:
            snapshot.status = "failed"
            snapshot.error = str(exc)
            snapshot.completed_at = datetime.now(timezone.utc)
        db.commit()
    finally:
        db.close()


@app.get("/")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "ares-twin-mission-control"}


@app.post("/telemetry", response_model=MissionAssessment)
def post_telemetry(
    telemetry: RoverTelemetry,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_session),
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

    log = MissionLog(
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
    db.add(log)
    db.commit()
    db.refresh(log)

    if assessment.status == "critical":
        video = MissionVideo(
            mission_log_id=log.id,
            status="pending" if settings.enable_media_generation else "disabled",
            prompt=veo_client.build_prompt(telemetry, assessment),
        )
        db.add(video)
        db.commit()
        db.refresh(video)
        if settings.enable_media_generation:
            background_tasks.add_task(_run_video_generation, video.id)

    qx, qy = _quadrant(telemetry.x, telemetry.y)
    existing = db.scalar(
        select(TerrainSnapshot).where(
            TerrainSnapshot.quadrant_x == qx,
            TerrainSnapshot.quadrant_y == qy,
        )
    )
    if existing is None:
        snapshot = TerrainSnapshot(
            quadrant_x=qx,
            quadrant_y=qy,
            status="pending" if settings.enable_media_generation else "disabled",
            prompt=nano_banana_client.build_prompt(qx, qy),
        )
        db.add(snapshot)
        db.commit()
        db.refresh(snapshot)
        if settings.enable_media_generation:
            background_tasks.add_task(_run_terrain_generation, snapshot.id)

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


@app.get("/mission-log/{log_id}/video")
def get_mission_video(
    log_id: int, db: Session = Depends(get_session)
) -> dict[str, object]:
    video = db.scalar(
        select(MissionVideo)
        .where(MissionVideo.mission_log_id == log_id)
        .order_by(MissionVideo.created_at.desc())
    )
    if video is None:
        raise HTTPException(status_code=404, detail="No video for this mission log")
    return {
        "id": video.id,
        "mission_log_id": video.mission_log_id,
        "status": video.status,
        "prompt": video.prompt,
        "video_url": f"/media/{video.video_path}" if video.video_path else None,
        "error": video.error,
        "created_at": video.created_at,
        "completed_at": video.completed_at,
    }


@app.get("/terrain/{qx}/{qy}")
def get_terrain(
    qx: int, qy: int, db: Session = Depends(get_session)
) -> dict[str, object]:
    snapshot = db.scalar(
        select(TerrainSnapshot).where(
            TerrainSnapshot.quadrant_x == qx,
            TerrainSnapshot.quadrant_y == qy,
        )
    )
    if snapshot is None:
        raise HTTPException(status_code=404, detail="No terrain snapshot for this quadrant")
    return {
        "id": snapshot.id,
        "quadrant_x": snapshot.quadrant_x,
        "quadrant_y": snapshot.quadrant_y,
        "status": snapshot.status,
        "prompt": snapshot.prompt,
        "image_url": f"/media/{snapshot.image_path}" if snapshot.image_path else None,
        "error": snapshot.error,
        "created_at": snapshot.created_at,
        "completed_at": snapshot.completed_at,
    }
