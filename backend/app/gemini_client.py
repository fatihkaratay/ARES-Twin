from google import genai
from google.genai import types

from .config import settings
from .schemas import MissionAssessment, RoverTelemetry

_client = genai.Client(api_key=settings.gemini_api_key)

SYSTEM_PROMPT = """You are the Mission Controller for a planetary rover digital twin.
Given a single telemetry packet (position, battery, motor torque) and any relevant
past events, classify rover health as nominal | caution | critical, explain the
reasoning in one or two sentences, and recommend a single concrete next action.
When past events are provided, reference them if they inform the decision."""


def assess(telemetry: RoverTelemetry, context: str = "") -> MissionAssessment:
    contents = telemetry.model_dump_json()
    if context:
        contents = f"{contents}\n\nRelevant past events:\n{context}"
    response = _client.models.generate_content(
        model=settings.gemini_model,
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            response_mime_type="application/json",
            response_schema=MissionAssessment,
        ),
    )
    return MissionAssessment.model_validate_json(response.text)
