from fastapi import APIRouter, Depends

from app.deps import get_current_user
from app import models, schemas
from app.services import image_service

router = APIRouter(prefix="/images", tags=["images"])


@router.post("/generate", response_model=schemas.ImageGenerateResponse)
def generate_image(payload: schemas.ImageGenerateRequest, user: models.User = Depends(get_current_user)):
    """
    Free text-to-image generation (no API key needed) - useful alongside a
    Groq vision model for a full "ask about images / create images" flow.
    """
    url = image_service.build_image_url(payload.prompt, payload.width, payload.height, payload.model)
    return schemas.ImageGenerateResponse(url=url)
