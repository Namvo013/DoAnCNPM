from typing import Any

from fastapi import APIRouter, Depends, File, UploadFile

from app.authz import require_permission
from app.services.images import ImageService

router = APIRouter(prefix="/admin/images", tags=["admin images"])
image_service = ImageService()


@router.post("/upload")
async def upload_image(
    file: UploadFile = File(...),
    _: dict[str, Any] = Depends(require_permission("poi:write")),
) -> dict[str, str]:
    return {"image_url": await image_service.upload(file)}
