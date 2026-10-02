"""Match APIs (MASTER_README §30, §34).

Matches are produced by the matching service; these endpoints let the users
involved review them, see *why* the AI suggested them, and track status.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from app import constants as C
from app.dependencies import get_current_user, get_db
from app.models import FoundItem, LostItem, Match, Message, User
from app.schemas import MatchStatusUpdate, MessageCreate
from app.services import matching_service
from app.services.notification_service import notify
from app.utils.helpers import page_payload, paginate, serialize_match, serialize_message

router = APIRouter(tags=["Matches"])


def _owned_ids(db: Session, user: User) -> tuple[list[int], list[int]]:
    lost_ids = [row[0] for row in db.query(LostItem.id).filter(LostItem.user_id == user.id).all()]
    found_ids = [row[0] for row in db.query(FoundItem.id).filter(FoundItem.user_id == user.id).all()]
    return lost_ids, found_ids


def _require_party(db: Session, match: Match, user: User) -> None:
    if user.role == C.ROLE_ADMIN:
        return
    lost_ids, found_ids = _owned_ids(db, user)
    if match.lost_item_id in lost_ids or match.found_item_id in found_ids:
        return
    raise HTTPException(status_code=403, detail="You are not part of this match")


def _load_match(db: Session, match_id: int) -> Match:
    match = (
        db.query(Match)
        .options(joinedload(Match.lost_item), joinedload(Match.found_item))
        .filter(Match.id == match_id)
        .first()
    )
    if match is None:
        raise HTTPException(status_code=404, detail="Match not found")
    return match


def _unread_by_match(db: Session, user_id: int, match_ids: list[int]) -> dict[int, int]:
    """Unread incoming message count per match, for badge display."""
    if not match_ids:
        return {}
    rows = (
        db.query(Message.match_id, func.count(Message.id))
        .filter(
            Message.match_id.in_(match_ids),
            Message.sender_id != user_id,
            Message.is_read.is_(False),
        )
        .group_by(Message.match_id)
        .all()
    )
    return {row[0]: row[1] for row in rows}


@router.get("/matches", summary="Matches involving my listings")
def list_matches(
    status: str | None = Query(None, description="POTENTIAL | VIEWED | CONTACTED | VERIFIED | REJECTED | RESOLVED"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    lost_ids, found_ids = _owned_ids(db, current_user)
    if not lost_ids and not found_ids:
        return page_payload([], 0, page, limit)

    query = (
        db.query(Match)
        .options(joinedload(Match.lost_item), joinedload(Match.found_item))
        .filter(or_(Match.lost_item_id.in_(lost_ids), Match.found_item_id.in_(found_ids)))
    )
    if status:
        query = query.filter(Match.status == status)
    query = query.order_by(Match.combined_score.desc(), Match.created_at.desc())
    items, total = paginate(query, page, limit)
    unread = _unread_by_match(db, current_user.id, [m.id for m in items])
    return page_payload(
        [
            dict(serialize_match(m), unread_messages=unread.get(m.id, 0))
            for m in items
        ],
        total,
        page,
        limit,
    )


@router.get("/matches/{match_id}", summary="Match details with AI explanation")
def get_match(
    match_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    match = (
        db.query(Match)
        .options(joinedload(Match.lost_item), joinedload(Match.found_item))
        .filter(Match.id == match_id)
        .first()
    )
    if match is None:
        raise HTTPException(status_code=404, detail="Match not found")
    _require_party(db, match, current_user)

    if match.status == C.MATCH_POTENTIAL:
        match.status = C.MATCH_VIEWED  # opening a match marks it as viewed
        db.commit()
        db.refresh(match)
    payload = serialize_match(match)
    payload["unread_messages"] = _unread_by_match(db, current_user.id, [match.id]).get(match.id, 0)
    return payload


@router.put("/matches/{match_id}/status", summary="Update match status")
def update_match_status(
    match_id: int,
    status_data: MatchStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    match = db.query(Match).filter(Match.id == match_id).first()
    if match is None:
        raise HTTPException(status_code=404, detail="Match not found")
    _require_party(db, match, current_user)
    match.status = status_data.status
    db.commit()
    db.refresh(match)
    return {"message": "Match status updated", "match": serialize_match(match)}


@router.get("/matches/{match_id}/messages", summary="Conversation between the two parties")
def list_messages(
    match_id: int,
    page: int = Query(1, ge=1),
    limit: int = Query(100, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    match = _load_match(db, match_id)
    _require_party(db, match, current_user)
    query = (
        db.query(Message)
        .options(joinedload(Message.sender))
        .filter(Message.match_id == match_id)
        .order_by(Message.created_at.asc(), Message.id.asc())
    )
    items, total = paginate(query, page, limit)
    return page_payload([serialize_message(m) for m in items], total, page, limit)


@router.post(
    "/matches/{match_id}/messages",
    status_code=201,
    summary="Send a message to the other party of the match",
)
def send_message(
    match_id: int,
    payload: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    match = _load_match(db, match_id)
    _require_party(db, match, current_user)

    body = payload.body.strip()
    if not body:
        raise HTTPException(status_code=422, detail="Message body cannot be empty")

    message = Message(match_id=match.id, sender_id=current_user.id, body=body)
    db.add(message)
    db.commit()
    db.refresh(message)

    # The first message moves POTENTIAL/VIEWED matches to CONTACTED; settled
    # statuses (VERIFIED/REJECTED/RESOLVED) are never downgraded automatically.
    if match.status in (C.MATCH_POTENTIAL, C.MATCH_VIEWED):
        match.status = C.MATCH_CONTACTED
        db.commit()
        db.refresh(match)

    # Notify the other party - never the sender (an admin sender notifies both).
    recipients = {
        uid
        for uid in (match.lost_item.user_id, match.found_item.user_id)
        if uid != current_user.id
    }
    snippet = body if len(body) <= 120 else body[:117] + "..."
    for recipient in recipients:
        notify(
            db,
            user_id=recipient,
            type=C.NOTIF_MESSAGE_RECEIVED,
            title=f"New message from {current_user.name}",
            message=(
                f'"{snippet}" - open Matches for "{match.lost_item.name}" / '
                f'"{match.found_item.name}" to reply.'
            ),
        )

    return {
        "message": "Message sent",
        "message_id": message.id,
        "match": serialize_match(match),
    }


@router.post("/matches/{match_id}/messages/read", summary="Mark incoming messages as read")
def mark_messages_read(
    match_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    match = _load_match(db, match_id)
    _require_party(db, match, current_user)
    updated = (
        db.query(Message)
        .filter(
            Message.match_id == match.id,
            Message.sender_id != current_user.id,
            Message.is_read.is_(False),
        )
        .update({"is_read": True}, synchronize_session=False)
    )
    db.commit()
    return {"message": f"Marked {updated} message(s) as read", "updated": updated}


@router.get("/messages/unread-count", summary="Unread message badge count")
def messages_unread_count(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    lost_ids, found_ids = _owned_ids(db, current_user)
    match_ids = [
        row[0]
        for row in db.query(Match.id)
        .filter(or_(Match.lost_item_id.in_(lost_ids), Match.found_item_id.in_(found_ids)))
        .all()
    ]
    count = 0
    if match_ids:
        count = (
            db.query(func.count(Message.id))
            .filter(
                Message.match_id.in_(match_ids),
                Message.sender_id != current_user.id,
                Message.is_read.is_(False),
            )
            .scalar()
            or 0
        )
    return {"unread": count}


@router.post("/matches/rebuild", summary="Re-run AI matching for my active listings")
def rebuild_matches(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    result = matching_service.run_for_user(db, current_user)
    return {
        "message": "Matching run complete",
        "new_matches": result["new_matches"],
    }
