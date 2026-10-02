"""Image upload endpoint (MASTER_README §16).

Validates type (magic bytes), rejects executables, enforces the size limit,
stores a server-generated filename and returns the public /media URL.
"""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.config import settings
from app.dependencies import get_current_user
from app.models import User
from app.services import image_service

router = APIRouter(tags=["Uploads"])


@router.post("/uploads", summary="Upload an item image (JPEG/PNG/WEBP)")
async def upload_image(
    file: UploadFile = File(...),
    _: User = Depends(get_current_user),
):
    content_type = (file.content_type or "").lower()
    if content_type and content_type not in {"image/jpeg", "image/png", "image/webp"}:
        # Cheap early rejection; image_service re-checks actual bytes.
        raise HTTPException(status_code=415, detail="Only JPEG, PNG or WEBP images are allowed")

    url = await image_service.save_upload(file)
    return {
        "message": "Image uploaded successfully",
        "url": url,
        "max_size_mb": settings.MAX_UPLOAD_SIZE_MB,
    }
