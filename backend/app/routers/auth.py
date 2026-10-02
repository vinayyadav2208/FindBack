"""Authentication endpoints: register, login, current user.

Flow (MASTER_README §9): register -> hash password -> login -> verify ->
JWT (with expiration) -> protected routes validate the JWT.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, get_db
from app.models import User
from app.schemas import TokenResponse, UserCreate, UserLogin, UserOut
from app.security import create_access_token, hash_password, verify_password

router = APIRouter(tags=["Authentication"])


def _register_user(db: Session, user_data: UserCreate) -> User:
    existing = db.query(User).filter(User.email == user_data.email).first()
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(
        name=user_data.name,
        email=user_data.email,
        password=hash_password(user_data.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _authenticate(db: Session, email: str, password: str) -> User:
    email = email.strip().lower()
    user = db.query(User).filter(User.email == email).first()

    if not user or not verify_password(password, user.password):
        # Same message for "unknown email" and "wrong password" (§55).
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="This account has been suspended")

    return user


def _issue_token(user: User) -> TokenResponse:
    token = create_access_token({"user_id": user.id, "email": user.email})
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserOut(
            id=user.id,
            name=user.name,
            email=user.email,
            role=user.role,
            created_at=user.created_at,
        ),
    )


@router.post(
    "/users",
    summary="Register a user (legacy endpoint, kept for compatibility)",
    response_description="Created user summary",
)
def create_user(user_data: UserCreate, db: Session = Depends(get_db)):
    user = _register_user(db, user_data)
    return {
        "message": "User created successfully",
        "user_id": user.id,
        "name": user.name,
        "email": user.email,
    }


@router.post(
    "/auth/register",
    status_code=201,
    summary="Register a new user and receive a token",
    response_model=TokenResponse,
)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    user = _register_user(db, user_data)
    return _issue_token(user)


@router.post(
    "/login",
    summary="Login with OAuth2 password form (legacy endpoint)",
    response_description="Access token",
)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = _authenticate(db, form_data.username, form_data.password)
    access_token = create_access_token({"user_id": user.id, "email": user.email})
    return {"access_token": access_token, "token_type": "bearer"}


@router.post(
    "/auth/login",
    summary="Login with JSON credentials",
    response_model=TokenResponse,
)
def login_json(payload: UserLogin, db: Session = Depends(get_db)):
    user = _authenticate(db, payload.email, payload.password)
    return _issue_token(user)


@router.get(
    "/me",
    summary="Current authenticated user",
    response_model=UserOut,
)
def get_me(current_user: User = Depends(get_current_user)):
    return UserOut(
        id=current_user.id,
        name=current_user.name,
        email=current_user.email,
        role=current_user.role,
        created_at=current_user.created_at,
    )
