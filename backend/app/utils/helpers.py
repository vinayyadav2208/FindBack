"""Serialization helpers keeping API responses consistent (MASTER_README §59)."""

from __future__ import annotations

import math
from typing import Any, Iterable

from app.config import settings


def clamp_pagination(page: Any, limit: Any) -> tuple[int, int]:
    try:
        page = int(page) if page is not None else 1
    except (TypeError, ValueError):
        page = 1
    try:
        limit = int(limit) if limit is not None else settings.DEFAULT_PAGE_LIMIT
    except (TypeError, ValueError):
        limit = settings.DEFAULT_PAGE_LIMIT
    page = max(page, 1)
    limit = max(1, min(limit, settings.MAX_PAGE_LIMIT))
    return page, limit


def paginate(query, page: int, limit: int) -> tuple[list, int]:
    """Apply offset/limit to a SQLAlchemy query, returning (items, total)."""
    total = query.count()
    items = query.offset((page - 1) * limit).limit(limit).all()
    return items, total


def page_payload(items: Iterable[dict], total: int, page: int, limit: int) -> dict:
    items = list(items)
    return {
        "items": items,
        "total": total,
        "page": page,
        "limit": limit,
        "pages": max(1, math.ceil(total / limit)) if total else 0,
    }


def serialize_user(user) -> dict:
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "is_active": user.is_active,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }


def serialize_lost_item(item, *, include_user: bool = True) -> dict:
    payload = {
        "id": item.id,
        "name": item.name,
        "description": item.description,
        "category": getattr(item, "category", None),
        "location": item.location,
        "latitude": getattr(item, "latitude", None),
        "longitude": getattr(item, "longitude", None),
        "status": getattr(item, "status", None),
        "images": getattr(item, "images", None) or [],
        "user_id": item.user_id,
        "user_name": item.user.name if (include_user and item.user) else None,
        "created_at": item.created_at.isoformat() if item.created_at else None,
        "updated_at": item.updated_at.isoformat() if item.updated_at else None,
    }
    return payload


def serialize_found_item(item, *, include_user: bool = True) -> dict:
    payload = serialize_lost_item(item, include_user=include_user)
    return payload


def serialize_donation(item, *, include_user: bool = True) -> dict:
    payload = serialize_lost_item(item, include_user=include_user)
    payload["condition"] = getattr(item, "condition", None)
    return payload


def serialize_claim(claim, claimant_name: str | None = None) -> dict:
    return {
        "id": claim.id,
        "item_type": claim.item_type,
        "item_id": claim.item_id,
        "claimant_id": claim.claimant_id,
        "claimant_name": claimant_name
        or (claim.claimant.name if getattr(claim, "claimant", None) else None),
        "message": claim.message,
        "verification_answers": claim.verification_answers,
        "status": claim.status,
        "review_note": claim.review_note,
        "created_at": claim.created_at.isoformat() if claim.created_at else None,
        "updated_at": claim.updated_at.isoformat() if claim.updated_at else None,
    }


def serialize_match(match) -> dict:
    lost = getattr(match, "lost_item", None)
    found = getattr(match, "found_item", None)
    return {
        "id": match.id,
        "lost_item_id": match.lost_item_id,
        "found_item_id": match.found_item_id,
        "text_score": match.text_score or 0.0,
        "image_score": match.image_score or 0.0,
        "location_score": match.location_score or 0.0,
        "category_score": match.category_score or 0.0,
        "combined_score": match.combined_score or 0.0,
        "status": match.status,
        "explanation": match.explanation,
        "created_at": match.created_at.isoformat() if match.created_at else None,
        "lost_item": serialize_lost_item(lost) if lost else None,
        "found_item": serialize_found_item(found) if found else None,
    }


def serialize_notification(notification) -> dict:
    return {
        "id": notification.id,
        "user_id": notification.user_id,
        "type": notification.type,
        "title": notification.title,
        "message": notification.message,
        "is_read": bool(notification.is_read),
        "created_at": notification.created_at.isoformat() if notification.created_at else None,
    }


def serialize_message(message) -> dict:
    sender = getattr(message, "sender", None)
    return {
        "id": message.id,
        "match_id": message.match_id,
        "sender_id": message.sender_id,
        "sender_name": sender.name if sender else None,
        "body": message.body,
        "is_read": bool(message.is_read),
        "created_at": message.created_at.isoformat() if message.created_at else None,
    }


def serialize_report(report) -> dict:
    return {
        "id": report.id,
        "reporter_id": report.reporter_id,
        "target_type": report.target_type,
        "target_id": report.target_id,
        "reason": report.reason,
        "description": report.description,
        "status": report.status,
        "created_at": report.created_at.isoformat() if report.created_at else None,
    }


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in kilometres (used by /nearby and distance filters)."""
    radius = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * radius * math.asin(math.sqrt(a))
