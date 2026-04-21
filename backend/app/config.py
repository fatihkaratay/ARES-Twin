from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = BACKEND_ROOT.parent / ".env"
DEFAULT_MEDIA_DIR = BACKEND_ROOT / "media"


class Settings(BaseSettings):
    gemini_api_key: str
    gemini_model: str = "gemini-2.5-flash"
    gemini_embedding_model: str = "gemini-embedding-001"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"
    database_url: str = "postgresql+psycopg2://ares:ares@localhost:5433/ares_twin"
    veo_model: str = "veo-3.1-fast-generate-preview"
    nano_banana_model: str = "gemini-2.5-flash-image"
    enable_media_generation: bool = False
    media_dir: Path = DEFAULT_MEDIA_DIR

    model_config = SettingsConfigDict(env_file=ENV_FILE, env_file_encoding="utf-8")


settings = Settings()

(settings.media_dir / "videos").mkdir(parents=True, exist_ok=True)
(settings.media_dir / "terrain").mkdir(parents=True, exist_ok=True)
