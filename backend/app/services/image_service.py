"""
Image capabilities offered to the user:

1. Vision Q&A - handled directly in groq_client via VISION_CAPABLE_MODELS,
   the user just picks a vision-capable Groq model and attaches an image.

2. Free text-to-image generation - Pollinations.ai requires no API key and is
   used here as the default free option. Swap in Stability/Hugging Face
   Inference API easily by adding another branch below if the user has keys
   for those.
"""
from urllib.parse import quote

from app.config import settings

AVAILABLE_IMAGE_MODELS = [
    {"id": "flux", "label": "Flux (best quality, free via Pollinations)"},
    {"id": "turbo", "label": "Turbo (fastest, free via Pollinations)"},
]


def build_image_url(prompt: str, width: int = 1024, height: int = 1024, model: str = "flux") -> str:
    encoded_prompt = quote(prompt)
    return (
        f"{settings.image_gen_base_url}/{encoded_prompt}"
        f"?width={width}&height={height}&model={model}&nologo=true"
    )
