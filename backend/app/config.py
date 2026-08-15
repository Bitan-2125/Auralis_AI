"""
Central application settings, loaded from environment variables (.env).
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --- Database ---
    database_url: str = "postgresql://postgres:postgres@postgres:5432/groqchat"

    # --- Auth ---
    secret_key: str = "change-me-in-production-please"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7  # 7 days

    # --- Groq ---
    groq_api_key: str = ""
    groq_api_base: str = "https://api.groq.com/openai/v1"

    # --- Chroma (RAG vector store) ---
    chroma_host: str = "chroma"
    chroma_port: int = 8000

    # --- Embeddings ---
    embedding_model: str = "all-MiniLM-L6-v2"

    # --- CORS ---
    frontend_origin: str = "http://localhost:5173"

    # --- Free image generation (no API key required) ---
    image_gen_base_url: str = "https://image.pollinations.ai/prompt"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()

# Curated capability metadata for Groq models. Groq's /models endpoint tells us
# which models exist right now, but not which ones accept image input or are
# meant for chat vs. audio/moderation - we maintain that mapping here and it's
# the only place you need to touch when Groq ships/retires a model.
VISION_CAPABLE_MODELS = {
    "qwen/qwen3.6-27b",
    "meta-llama/llama-4-scout-17b-16e-instruct",
    "meta-llama/llama-4-maverick-17b-128e-instruct",
}

# Models that exist on Groq but are not chat-completion models (audio, TTS,
# moderation, embeddings-adjacent) - filtered out of the chat model picker.
NON_CHAT_MODEL_PREFIXES = (
    "whisper",
    "canopylabs",
    "distil-whisper",
    "playai-tts",
)

RECOMMENDED_CHAT_MODELS = [
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
    "qwen/qwen3.6-27b",
    "moonshotai/kimi-k2",
]
