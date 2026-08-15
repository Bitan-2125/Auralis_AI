from typing import List

from fastapi import APIRouter, Depends

from app.deps import get_current_user
from app import models, schemas
from app.services import groq_client, image_service

router = APIRouter(prefix="/models", tags=["models"])


@router.get("/chat", response_model=List[schemas.ModelInfo])
def list_chat_models(user: models.User = Depends(get_current_user)):
    """Live list of Groq chat/vision models the user can pick from."""
    return groq_client.list_models()


@router.get("/image")
def list_image_models(user: models.User = Depends(get_current_user)):
    """Free image-generation model options (no API key required)."""
    return image_service.AVAILABLE_IMAGE_MODELS
