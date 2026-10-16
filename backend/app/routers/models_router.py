from fastapi import APIRouter, Depends
from app.deps import get_current_user
from app.config import settings
from app import models, schemas
from app.services import providers

router = APIRouter(prefix="/models", tags=["models"])


@router.get("/chat", response_model=list[schemas.ModelInfo])
async def list_chat_models(user: models.User = Depends(get_current_user)):
    return await providers.list_models()


@router.get("/image")
def list_image_models(user: models.User = Depends(get_current_user)):
    from app.services.image_service import IMAGE_MODEL
    return [{"id": IMAGE_MODEL, "name": "FLUX.2 Klein 4B", "provider": "NVIDIA NIM", "available": bool(settings.nvidia_api_key)}]
