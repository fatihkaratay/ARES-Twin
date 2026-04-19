from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class RoverTelemetry(BaseModel):
    x: float
    y: float
    z: float
    battery: float = Field(ge=0, le=100, description="Battery percentage")
    motor_torque: float = Field(description="Aggregate motor torque in N·m")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class MissionAssessment(BaseModel):
    status: Literal["nominal", "caution", "critical"]
    reasoning: str
    recommended_action: str


class MissionLogEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    timestamp: datetime
    x: float
    y: float
    z: float
    battery: float
    motor_torque: float
    status: Literal["nominal", "caution", "critical"]
    reasoning: str
    recommended_action: str
