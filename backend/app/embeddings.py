from google import genai
from google.genai import types

from .config import settings
from .models import EMBEDDING_DIM

_client = genai.Client(api_key=settings.gemini_api_key)


def embed(text: str) -> list[float]:
    response = _client.models.embed_content(
        model=settings.gemini_embedding_model,
        contents=text,
        config=types.EmbedContentConfig(output_dimensionality=EMBEDDING_DIM),
    )
    return list(response.embeddings[0].values)
