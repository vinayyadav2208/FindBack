"""Shared direct-message thread logic (matches and claims).

Both thread kinds - a match (finder <-> loser) and a claim (donor/owner <->
requester) - use the same `messages` table and the same rules: only the
parties (and admins) may read/write, `is_read` means "read by the recipient",
and sending never fails the operation that triggered it (§68: notifications
are best effort).
"""

from __future__ import annotations

import logging

from sqlalchemy import func
from sqlalchemy.orm import Session

from app import constants as C
from app.models import Message, User
from app.services.notification_service import notify

logger = logging.getLogger("findback.messages")

MAX_BODY = 2000


def snippet(body: str) -> str:
    """First ~120 chars of a message for notification previews."""
    return body if len(body) <= 120 else body[:117] + "..."


def create_message(
    db: Session,
    *,
    sender_id: int,
    body: str,
    match_id: int | None = None,
    claim_id: int | None = None,
) -> Message:
    """Persist a message belonging to exactly one thread (match XOR claim)."""
    if (match_id is None) == (claim_id is None):
        raise ValueError("A message must target exactly one thread (match_id XOR claim_id)")
    message = Message(match_id=match_id, claim_id=claim_id, sender_id=sender_id, body=body)
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


def notify_new_message(
    db: Session,
    *,
    sender: User,
    recipients: set[int],
    body: str,
    context: str,
    related_type: str,
    related_id: int,
) -> None:
    """Tell every recipient except the sender that a new message arrived.

    `context` names the thread ("Matches for 'X' / 'Y'" or "the claim on 'X'").
    """
    preview = snippet(body)
    for recipient in recipients:
        if recipient == sender.id:
            continue
        notify(
            db,
            user_id=recipient,
            type=C.NOTIF_MESSAGE_RECEIVED,
            title=f"New message from {sender.name}",
            message=f'"{preview}" - open {context} to reply.',
            related_type=related_type,
            related_id=related_id,
        )


def unread_map(
    db: Session, *, user_id: int, column, thread_ids: list[int]
) -> dict[int, int]:
    """Unread incoming message count per thread, for badge display.

    `column` is Message.match_id or Message.claim_id.
    """
    if not thread_ids:
        return {}
    rows = (
        db.query(column, func.count(Message.id))
        .filter(
            column.in_(thread_ids),
            Message.sender_id != user_id,
            Message.is_read.is_(False),
        )
        .group_by(column)
        .all()
    )
    return {row[0]: row[1] for row in rows}


def mark_read(db: Session, *, user_id: int, column, thread_id: int) -> int:
    """Mark all incoming messages in one thread as read; returns how many."""
    updated = (
        db.query(Message)
        .filter(
            column == thread_id,
            Message.sender_id != user_id,
            Message.is_read.is_(False),
        )
        .update({"is_read": True}, synchronize_session=False)
    )
    db.commit()
    return updated
