"""Image upload validation and optional image similarity (§16, §32).

Uploads are validated by magic bytes (never trusting the client), size-
limited, and stored under a random server-generated filename inside MEDIA_DIR.
Image similarity uses CLIP when available and otherwise degrades to:
  * 1.0 when both listings reference the exact same stored image
  * None when no comparison is possible (matching then renormalizes weights)
"""

from __future__ import annotations

import logging
import secrets
from pathlib import Path

from fastapi import HTTPException, UploadFile

from app.config import settings

logger = logging.getLogger("findback.images")

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
MAX_BYTES = settings.MAX_UPLOAD_BYTES
MEDIA_DIR: Path = settings.MEDIA_DIR

_magic_signatures = (
    (b"\xff\xd8\xff", (".jpg", ".jpeg")),
    (b"\x89PNG\r\n\x1a\n", (".png",)),
)


def _sniff(data: bytes) -> str | None:
    for signature, extensions in _magic_signatures:
        if data.startswith(signature):
            return extensions[0]
    if len(data) >= 12 and data[0:4] == b"RIFF" and data[8:12] == b"WEBP":
        return ".webp"
    return None  # also rejects executables (§16)


async def save_upload(file: UploadFile) -> str:
    """Validate + store one uploaded image; returns its public URL path."""
    contents = await file.read(MAX_BYTES + 1)
    if len(contents) > MAX_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"Image exceeds the {settings.MAX_UPLOAD_SIZE_MB} MB limit",
        )
    if not contents:
        raise HTTPException(status_code=400, detail="Empty file")

    ext = _sniff(contents)
    if ext is None:
        raise HTTPException(
            status_code=415,
            detail="Unsupported file type. Allowed: JPEG, PNG, WEBP",
        )

    original_name = (file.filename or "").lower()
    if original_name.endswith((".exe", ".bat", ".cmd", ".sh", ".js", ".html", ".php")):
        raise HTTPException(status_code=415, detail="Executable files are not allowed")

    MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    stored_name = f"{secrets.token_hex(16)}{ext}"  # safe generated filename (§16)
    (MEDIA_DIR / stored_name).write_bytes(contents)
    return f"/media/{stored_name}"


def local_path_for(url: str) -> Path | None:
    """Map a stored /media/<name> URL back to its local file, if it exists."""
    if not url or not url.startswith("/media/"):
        return None
    name = url.removeprefix("/media/")
    if not name or "/" in name or "\\" in name or ".." in name:
        return None
    path = MEDIA_DIR / name
    return path if path.is_file() else None


def _clip_similarity(path_a: Path, path_b: Path) -> float | None:
    """CLIP-based similarity when the optional stack is installed (§32)."""
    try:
        import torch
        from PIL import Image

        try:
            import open_clip
        except Exception:
            return None  # open-clip not installed

        model, _, preprocess = open_clip.create_model_and_transforms(
            "ViT-B-32", pretrained="laion2b_s34b_b79k"
        )
        tokenizer = open_clip.get_tokenizer("ViT-B-32")
        model.eval()
        with torch.no_grad():
            image_features = model.encode_image(
                preprocess(Image.open(path_a)).unsqueeze(0)
            )
            other_features = model.encode_image(
                preprocess(Image.open(path_b)).unsqueeze(0)
            )
            image_features /= image_features.norm(dim=-1, keepdim=True)
            other_features /= other_features.norm(dim=-1, keepdim=True)
            score = float((image_features @ other_features.T).item())
        return max(0.0, min(1.0, score))
    except Exception as exc:
        logger.info("CLIP similarity unavailable (%s)", exc.__class__.__name__)
        return None


def similarity(item_a, item_b) -> float | None:
    """Image similarity between two listings: float in [0,1] or None."""
    images_a = list(getattr(item_a, "images", None) or [])
    images_b = list(getattr(item_b, "images", None) or [])
    if not images_a or not images_b:
        return None

    if set(images_a) & set(images_b):
        return 1.0  # the exact same stored image appears in both listings

    # Try CLIP on the first stored image pair (optional backend).
    path_a = next((p for p in (local_path_for(u) for u in images_a) if p), None)
    path_b = next((p for p in (local_path_for(u) for u in images_b) if p), None)
    if path_a and path_b:
        score = _clip_similarity(path_a, path_b)
        if score is not None:
            return score
    return None
