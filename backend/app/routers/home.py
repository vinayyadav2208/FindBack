"""Home / status endpoints (kept from the original implementation)."""

from fastapi import APIRouter

router = APIRouter(tags=["Home"])


@router.get("/", summary="API welcome")
def home():
    return {"message": "Welcome to FindBack API"}


@router.get("/hello", summary="Legacy hello endpoint")
def hello():
    return {"message": "Hello Vinay!"}


@router.get("/health", summary="Liveness probe")
def health():
    return {"status": "ok", "service": "findback"}
