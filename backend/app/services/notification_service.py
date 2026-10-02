"""Notification creation (MASTER_README §35, §37).

REST-only for now; the service is isolated so a WebSocket layer can be added
later without touching routers. `notify()` never raises - a notification
failure must not break the operation that triggered it (§68).
"""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app import constants as C
from app.models import Notification

logger = logging.getLogger("findback.notifications")


def notify(
    db: Session,
    *,
    user_id: int | None,
    title: str,
    message: str | None = None,
    type: str = C.NOTIF_SYSTEM,
) -> Notification | None:
    """Create a notification for a user; returns None on failure (never raises)."""
    if not user_id:
        return None
    try:
        notification = Notification(
            user_id=user_id,
            type=type,
            title=title[:200],
            message=message,
        )
        db.add(notification)
        db.commit()
        return notification
    except Exception:
        logger.exception("Failed to create notification for user %s", user_id)
        try:
            db.rollback()
        except Exception:
            pass
        return None


def unread_count(db: Session, user_id: int) -> int:
    return (
        db.query(Notification)
        .filter(Notification.user_id == user_id, Notification.is_read.is_(False))
        .count()
    )
