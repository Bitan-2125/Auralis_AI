"""
Central application settings, loaded from environment variables (.env).
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --- Database ---
    database_url: str = "sqlite:///./chat.db"

    # --- Auth ---
    secret_key: str = "change-me-in-production-please"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7  # 7 days

    # --- AgentRouter ---
    agentrouter_api_key: str = "sk-rq1JDsRevKZ67CM6qFtzoh5r5dTSsRJ2LziNVH9VNtqwwNZc"
    agentrouter_base_url: str = "https://agentrouter.org/v1"

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

# AgentRouter Models
AGENTROUTER_MODELS = [
    {
        "id": "deepseek-v4-flash",
        "name": "DeepSeek V4 Flash",
        "provider": "AgentRouter",
        "description": "Ultra-fast reasoning model with live token streaming",
        "context_window": 128000,
        "supports_vision": False,
    },
    {
        "id": "glm-5.3",
        "name": "GLM 5.3",
        "provider": "AgentRouter",
        "description": "High-capability general reasoning model",
        "context_window": 128000,
        "supports_vision": False,
    },
    {
        "id": "gpt-5.6-sol",
        "name": "GPT 5.6 Sol",
        "provider": "AgentRouter",
        "description": "Next-generation OpenAI Sol architecture",
        "context_window": 128000,
        "supports_vision": False,
    },
    {
        "id": "claude-opus-4-8",
        "name": "Claude Opus 4.8",
        "provider": "AgentRouter",
        "description": "Flagship Claude Opus 4.8 reasoning model",
        "context_window": 200000,
        "supports_vision": False,
    },
    {
        "id": "claude-opus-5",
        "name": "Claude Opus 5",
        "provider": "AgentRouter",
        "description": "Next-generation Claude Opus 5 model",
        "context_window": 200000,
        "supports_vision": False,
    },
]

AGENTROUTER_MODEL_IDS = {m["id"] for m in AGENTROUTER_MODELS}

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
    "deepseek-v4-flash",
    "glm-5.3",
    "gpt-5.6-sol",
    "claude-opus-4-8",
    "claude-opus-5",
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
    "qwen/qwen3.6-27b",
    "moonshotai/kimi-k2",
]
