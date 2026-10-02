"""Match APIs (MASTER_README §30, §34).

Matches are produced by the matching service; these endpoints let the users
involved review them, see *why* the AI suggested them, and track status.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app import constants as C
from app.dependencies import get_current_user, get_db
from app.models import FoundItem, LostItem, Match, User
from app.schemas import MatchStatusUpdate
from app.services import matching_service
from app.utils.helpers import page_payload, paginate, serialize_match

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
    return page_payload([serialize_match(m) for m in items], total, page, limit)


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
    return serialize_match(match)


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
