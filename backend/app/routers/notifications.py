"""Notification APIs (MASTER_README §35, §36)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, get_db
from app.models import Notification, User
from app.services.notification_service import unread_count
from app.utils.helpers import page_payload, paginate, serialize_notification

router = APIRouter(tags=["Notifications"])


@router.get("/notifications", summary="My notifications")
def list_notifications(
    unread_only: bool = False,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Notification).filter(Notification.user_id == current_user.id)
    if unread_only:
        query = query.filter(Notification.is_read.is_(False))
    query = query.order_by(Notification.created_at.desc(), Notification.id.desc())
    items, total = paginate(query, page, limit)
    payload = page_payload([serialize_notification(n) for n in items], total, page, limit)
    payload["unread"] = unread_count(db, current_user.id)
    return payload


@router.get("/notifications/unread-count", summary="Unread notification badge count")
def notification_unread_count(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return {"unread": unread_count(db, current_user.id)}


@router.put("/notifications/{notification_id}/read", summary="Mark one notification read")
def mark_read(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    notification = (
        db.query(Notification)
        .filter(
            Notification.id == notification_id,
            Notification.user_id == current_user.id,
        )
        .first()
    )
    if notification is None:
        raise HTTPException(status_code=404, detail="Notification not found")
    notification.is_read = True
    db.commit()
    return {"message": "Notification marked as read", "notification": serialize_notification(notification)}


@router.put("/notifications/read-all", summary="Mark all my notifications read")
def mark_all_read(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    updated = (
        db.query(Notification)
        .filter(
            Notification.user_id == current_user.id,
            Notification.is_read.is_(False),
        )
        .update({"is_read": True}, synchronize_session=False)
    )
    db.commit()
    return {"message": f"Marked {updated} notification(s) as read", "updated": updated}
