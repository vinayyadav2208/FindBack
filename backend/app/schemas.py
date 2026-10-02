"""Pydantic request/response schemas.

Security rule (MASTER_README §14): creation/update payloads NEVER accept
`user_id` - ownership always comes from the JWT of the authenticated user.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator

from app import constants as C

EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")


def _check_category(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    normalized = value.strip()
    if normalized not in C.CATEGORIES:
        raise ValueError(
            f"Unknown category '{normalized}'. Valid categories: {', '.join(C.CATEGORIES)}"
        )
    return normalized


def _check_latitude(value: Optional[float]) -> Optional[float]:
    if value is not None and not -90.0 <= value <= 90.0:
        raise ValueError("latitude must be between -90 and 90")
    return value


def _check_longitude(value: Optional[float]) -> Optional[float]:
    if value is not None and not -180.0 <= value <= 180.0:
        raise ValueError("longitude must be between -180 and 180")
    return value


# =========================
# AUTH
# =========================

class UserCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: str = Field(..., max_length=100)
    password: str = Field(..., min_length=8, max_length=128)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        value = value.strip().lower()
        if not EMAIL_RE.match(value):
            raise ValueError("Invalid email address")
        return value

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Name must not be empty")
        return value


class UserLogin(BaseModel):
    email: str
    password: str


class UserOut(BaseModel):
    id: int
    name: str
    email: str
    role: str = C.ROLE_USER
    created_at: Optional[datetime] = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: Optional[UserOut] = None


# =========================
# LOST ITEMS
# =========================

class LostItemCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., min_length=1, max_length=2000)
    category: str = C.DEFAULT_CATEGORY
    location: str = Field(..., min_length=1, max_length=100)
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    images: Optional[list[str]] = None

    _check_category = field_validator("category")(_check_category)
    _check_latitude = field_validator("latitude")(_check_latitude)
    _check_longitude = field_validator("longitude")(_check_longitude)


class LostItemUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, min_length=1, max_length=2000)
    category: Optional[str] = None
    location: Optional[str] = Field(None, min_length=1, max_length=100)
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    images: Optional[list[str]] = None
    status: Optional[str] = None

    _check_category = field_validator("category")(_check_category)
    _check_latitude = field_validator("latitude")(_check_latitude)
    _check_longitude = field_validator("longitude")(_check_longitude)

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and value not in C.LOST_STATUSES:
            raise ValueError(f"Invalid status. Valid: {', '.join(C.LOST_STATUSES)}")
        return value


# =========================
# FOUND ITEMS
# =========================

class FoundItemCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., min_length=1, max_length=2000)
    category: str = C.DEFAULT_CATEGORY
    location: str = Field(..., min_length=1, max_length=100)
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    images: Optional[list[str]] = None

    _check_category = field_validator("category")(_check_category)
    _check_latitude = field_validator("latitude")(_check_latitude)
    _check_longitude = field_validator("longitude")(_check_longitude)


class FoundItemUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, min_length=1, max_length=2000)
    category: Optional[str] = None
    location: Optional[str] = Field(None, min_length=1, max_length=100)
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    images: Optional[list[str]] = None
    status: Optional[str] = None

    _check_category = field_validator("category")(_check_category)
    _check_latitude = field_validator("latitude")(_check_latitude)
    _check_longitude = field_validator("longitude")(_check_longitude)

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and value not in C.FOUND_STATUSES:
            raise ValueError(f"Invalid status. Valid: {', '.join(C.FOUND_STATUSES)}")
        return value


# =========================
# DONATIONS
# =========================

class DonationCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., min_length=1, max_length=2000)
    category: str = C.DEFAULT_CATEGORY
    condition: str = C.CONDITION_GOOD
    location: str = Field(..., min_length=1, max_length=100)
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    images: Optional[list[str]] = None

    _check_category = field_validator("category")(_check_category)
    _check_latitude = field_validator("latitude")(_check_latitude)
    _check_longitude = field_validator("longitude")(_check_longitude)

    @field_validator("condition")
    @classmethod
    def validate_condition(cls, value: str) -> str:
        if value not in C.CONDITIONS:
            raise ValueError(f"Invalid condition. Valid: {', '.join(C.CONDITIONS)}")
        return value


class DonationUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, min_length=1, max_length=2000)
    category: Optional[str] = None
    condition: Optional[str] = None
    location: Optional[str] = Field(None, min_length=1, max_length=100)
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    images: Optional[list[str]] = None
    status: Optional[str] = None

    _check_category = field_validator("category")(_check_category)
    _check_latitude = field_validator("latitude")(_check_latitude)
    _check_longitude = field_validator("longitude")(_check_longitude)

    @field_validator("condition")
    @classmethod
    def validate_condition(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and value not in C.CONDITIONS:
            raise ValueError(f"Invalid condition. Valid: {', '.join(C.CONDITIONS)}")
        return value

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and value not in C.DONATION_STATUSES:
            raise ValueError(f"Invalid status. Valid: {', '.join(C.DONATION_STATUSES)}")
        return value


# =========================
# CLAIMS
# =========================

class ClaimCreate(BaseModel):
    message: Optional[str] = Field(None, max_length=2000)
    # Private answers used for ownership verification (§26) - never public.
    verification_answers: Optional[dict[str, str]] = None


class ClaimReview(BaseModel):
    note: Optional[str] = Field(None, max_length=2000)


class ClaimOut(BaseModel):
    id: int
    item_type: str
    item_id: int
    claimant_id: int
    claimant_name: Optional[str] = None
    message: Optional[str] = None
    verification_answers: Optional[dict[str, Any]] = None
    status: str
    review_note: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# =========================
# MATCHES
# =========================

class MatchStatusUpdate(BaseModel):
    status: str

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        if value not in C.MATCH_STATUSES:
            raise ValueError(f"Invalid status. Valid: {', '.join(C.MATCH_STATUSES)}")
        return value


class MessageCreate(BaseModel):
    body: str = Field(..., min_length=1, max_length=2000)


class MatchOut(BaseModel):
    id: int
    lost_item_id: int
    found_item_id: int
    text_score: float = 0.0
    image_score: float = 0.0
    location_score: float = 0.0
    category_score: float = 0.0
    combined_score: float = 0.0
    status: str = C.MATCH_POTENTIAL
    explanation: Optional[dict[str, Any]] = None
    created_at: Optional[datetime] = None
    lost_item: Optional[dict[str, Any]] = None
    found_item: Optional[dict[str, Any]] = None


# =========================
# NOTIFICATIONS
# =========================

class NotificationOut(BaseModel):
    id: int
    user_id: int
    type: str
    title: str
    message: Optional[str] = None
    is_read: bool = False
    created_at: Optional[datetime] = None


# =========================
# REPORTS
# =========================

class ReportCreate(BaseModel):
    target_type: str
    target_id: int
    reason: str = Field(..., max_length=100)
    description: Optional[str] = Field(None, max_length=2000)

    @field_validator("target_type")
    @classmethod
    def validate_target_type(cls, value: str) -> str:
        if value not in C.REPORT_TARGETS:
            raise ValueError(f"Invalid target type. Valid: {', '.join(C.REPORT_TARGETS)}")
        return value

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, value: str) -> str:
        value = value.strip().upper()
        if value not in C.REPORT_REASONS:
            raise ValueError(f"Invalid reason. Valid: {', '.join(C.REPORT_REASONS)}")
        return value


class ReportReview(BaseModel):
    status: str

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        if value not in C.REPORT_STATUSES:
            raise ValueError(f"Invalid status. Valid: {', '.join(C.REPORT_STATUSES)}")
        return value


class ReportOut(BaseModel):
    id: int
    reporter_id: int
    target_type: str
    target_id: int
    reason: str
    description: Optional[str] = None
    status: str
    created_at: Optional[datetime] = None
