from fastapi import FastAPI

from .gemini_client import assess
from .schemas import MissionAssessment, RoverTelemetry

app = FastAPI(title="ARES-Twin Mission Control")


@app.get("/")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "ares-twin-mission-control"}


@app.post("/telemetry", response_model=MissionAssessment)
def post_telemetry(telemetry: RoverTelemetry) -> MissionAssessment:
    return assess(telemetry)
