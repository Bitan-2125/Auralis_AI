"""Server-only configuration. Provider credentials never go to the browser."""
from pathlib import Path
import os
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    database_url: str = "sqlite:///./chat.db"
    secret_key: str = "change-me-in-production-please"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7
    groq_api_key: str = ""
    groq_api_base: str = "https://api.groq.com/openai/v1"
    nvidia_api_key: str = ""
    nvidia_api_base: str = "https://integrate.api.nvidia.com/v1"
    nvidia_image_url: str = "https://ai.api.nvidia.com/v1/genai/black-forest-labs/flux.2-klein-4b"
    agentrouter_api_key: str = ""
    agentrouter_base_url: str = "https://agentrouter.org/v1"
    agentrouter_models: str = ""
    tavily_api_key: str = ""
    web_search_router_model: str = ""
    frontend_origin: str = "http://localhost:5173"
    context_char_budget: int = Field(default=24000, ge=20000, le=100000)
    max_completion_tokens: int = Field(default=2048, ge=128, le=8192)
    upload_max_mb: int = Field(default=4, ge=1, le=4)
    generation_timeout_seconds: int = Field(default=260, ge=30, le=270)
    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", extra="ignore")

    @model_validator(mode="after")
    def production_storage(self):
        if os.getenv("VERCEL") == "1":
            if not self.database_url.startswith(("postgres://", "postgresql://", "postgresql+psycopg://")):
                raise ValueError("Vercel requires a persistent PostgreSQL DATABASE_URL")
            if len(self.secret_key) < 32 or any(marker in self.secret_key.lower() for marker in ("change-me", "change-in-production", "replace-with")):
                raise ValueError("Set a random SECRET_KEY of at least 32 characters")
        return self


settings = Settings()
VISION_CAPABLE_MODELS = {
    "qwen/qwen3.8-27b", "qwen/qwen3.6-27b",
    "meta-llama/llama-4-scout-17b-16e-instruct",
    "meta-llama/llama-4-maverick-17b-128e-instruct",
}
NON_CHAT_MODEL_PREFIXES = (
    "whisper", "canopylabs", "distil-whisper", "playai", "meta-llama/llama-guard",
    "meta-llama/llama-prompt-guard", "openai/safeguard", "openai/gpt-oss-safeguard", "prompt-guard",
)
GROQ_FALLBACK_MODELS = ["openai/gpt-oss-20b", "openai/gpt-oss-120b", "qwen/qwen3.8-27b"]
NVIDIA_MODELS = [
    ("openai/gpt-oss-20b", "GPT OSS 20B"),
    ("nvidia/nemotron-3.5-lightning-30b-a3b", "Nemotron 3.5 Lightning"),
    ("nvidia/nemotron-3-super-120b-a12b", "Nemotron 3 Super"),
    ("nvidia/nemotron-3-ultra-550b-a55b", "Nemotron 3 Ultra"),
    ("deepseek-ai/deepseek-v4.1-flash", "DeepSeek V4.1 Flash"),
    ("moonshotai/kimi-k2.6", "Kimi K2.6"),
    ("z-ai/glm-5.3", "GLM 5.3"),
    ("z-ai/glm-5.3-flash", "GLM 5.3 Flash"),
    ("nvidia/llama-3.1-nemotron-70b-instruct", "Nemotron 70B"),
]
