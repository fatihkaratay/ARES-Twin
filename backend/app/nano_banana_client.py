from pathlib import Path

from google import genai

from .config import settings

_client = genai.Client(api_key=settings.gemini_api_key)


def build_prompt(quadrant_x: int, quadrant_y: int) -> str:
    return (
        f"Top-down 4K aerial photograph of Martian terrain, quadrant ({quadrant_x}, {quadrant_y}). "
        "Geologically realistic, consistent with NASA Jezero Crater orbital imagery: "
        "iron-oxide dust, scattered basalt rocks, shallow ridges, dried riverbed patterns, "
        "subtle wind ripples in the regolith. Satellite perspective, crisp detail, "
        "photorealistic, no human artifacts."
    )


def generate(prompt: str, output_path: Path) -> None:
    response = _client.models.generate_content(
        model=settings.nano_banana_model,
        contents=prompt,
    )
    for part in response.candidates[0].content.parts:
        if part.inline_data and part.inline_data.mime_type.startswith("image/"):
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(part.inline_data.data)
            return
    raise RuntimeError("Nano Banana returned no image part")
