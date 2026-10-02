"""Shared FastAPI dependencies (auth, database sessions, role guards)."""

from __future__ import annotations

from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app import constants as C
from app.database import SessionLocal
from app.models import User
from app.security import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    payload = decode_access_token(token)

    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user_id = payload.get("user_id")
    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="This account has been suspended")

    return user


def get_current_user_optional(
    token: str | None = Depends(OAuth2PasswordBearer(tokenUrl="login", auto_error=False)),
    db: Session = Depends(get_db),
) -> User | None:
    """Return the authenticated user when a valid token is supplied, else None."""
    if not token:
        return None
    payload = decode_access_token(token)
    if payload is None or payload.get("user_id") is None:
        return None
    user = db.query(User).filter(User.id == payload.get("user_id")).first()
    if user is None or not user.is_active:
        return None
    return user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != C.ROLE_ADMIN:
        raise HTTPException(status_code=403, detail="Admin privileges required")
    return current_user
