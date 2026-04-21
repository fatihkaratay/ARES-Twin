import time
from pathlib import Path

from google import genai

from .config import settings
from .schemas import MissionAssessment, RoverTelemetry

_client = genai.Client(api_key=settings.gemini_api_key)

POLL_INTERVAL_SECONDS = 10


def build_prompt(telemetry: RoverTelemetry, assessment: MissionAssessment) -> str:
    return (
        "Cinematic 4K video of a planetary rover on Mars executing a critical maneuver. "
        f"Rover position ({telemetry.x:.1f}, {telemetry.y:.1f}, {telemetry.z:.1f}) meters, "
        f"battery at {telemetry.battery:.0f}%, motor torque {telemetry.motor_torque:.2f} Nm. "
        f"Situation: {assessment.reasoning} "
        f"Planned response: {assessment.recommended_action}. "
        "Wide tracking shot, golden-hour Martian light, dust plume kicked up by wheels, "
        "iron-oxide regolith, realistic photographic quality."
    )


def generate(prompt: str, output_path: Path) -> None:
    operation = _client.models.generate_videos(
        model=settings.veo_model,
        prompt=prompt,
    )
    while not operation.done:
        time.sleep(POLL_INTERVAL_SECONDS)
        operation = _client.operations.get(operation)

    generated_video = operation.response.generated_videos[0]
    _client.files.download(file=generated_video.video)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    generated_video.video.save(str(output_path))
