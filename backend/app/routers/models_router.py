from typing import List

from fastapi import APIRouter, Depends

from app.deps import get_current_user
from app.config import AGENTROUTER_MODELS
from app import models, schemas
from app.services import groq_client, image_service

router = APIRouter(prefix="/models", tags=["models"])


@router.get("/chat", response_model=List[schemas.ModelInfo])
def list_chat_models(user: models.User = Depends(get_current_user)):
    """
    Returns available models from AgentRouter (gpt-5.6-sol, claude-opus-4-8,
    claude-opus-5, deepseek-v4-flash, glm-5.3) and Groq.
    """
    groq_models = groq_client.list_models()
    # Combine AgentRouter models first, followed by Groq models
    return list(AGENTROUTER_MODELS) + groq_models


@router.get("/image")
def list_image_models(user: models.User = Depends(get_current_user)):
    """Free image-generation model options (no API key required)."""
    return image_service.AVAILABLE_IMAGE_MODELS
