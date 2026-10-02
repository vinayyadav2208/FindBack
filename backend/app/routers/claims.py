"""Claim APIs (MASTER_README §25, §26).

Claims cover:
  - FOUND_ITEM : "this is mine" on someone's found listing
  - LOST_ITEM   : "I found this" on someone's lost listing
  - DONATION    : "I'd like this" (also available at POST /donations/{id}/claim)

Verification answers are private: only the claimant, the listing owner and
admins can read a claim (§70). Approval/rejection is always human-driven (§99).
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from app import constants as C
from app.dependencies import get_current_user, get_db
from app.models import Claim, Donation, FoundItem, LostItem, Message, User
from app.schemas import ClaimCreate, ClaimReview, MessageCreate
from app.services import claim_service, message_service
from app.utils.helpers import page_payload, paginate, serialize_claim, serialize_message

router = APIRouter(tags=["Claims"])


def _load_claim(db: Session, claim_id: int) -> Claim:
    claim = db.query(Claim).filter(Claim.id == claim_id).first()
    if claim is None:
        raise HTTPException(status_code=404, detail="Claim not found")
    return claim


def _can_view(db: Session, claim: Claim, user: User) -> bool:
    if user.role == C.ROLE_ADMIN or claim.claimant_id == user.id:
        return True
    item = claim_service.get_claim_item(db, claim.item_type, claim.item_id)
    return item.user_id == user.id


@router.post("/claims", status_code=201, summary="Submit a claim on a found item / lost listing")
def create_claim(
    claim_data: ClaimCreate,
    item_type: str = Query(..., description="FOUND_ITEM | LOST_ITEM | DONATION"),
    item_id: int = Query(..., description="ID of the listing being claimed"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item_type = item_type.strip().upper()
    if item_type not in C.CLAIM_ITEM_TYPES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid item type. Valid: {', '.join(C.CLAIM_ITEM_TYPES)}",
        )
    claim = claim_service.create_claim(
        db,
        item_type=item_type,
        item_id=item_id,
        user=current_user,
        message=claim_data.message,
        verification_answers=claim_data.verification_answers,
    )
    return {
        "message": "Claim submitted successfully",
        "claim_id": claim.id,
        "status": claim.status,
    }


@router.get("/my-claims", summary="Claims submitted by the current user")
def list_my_claims(
    status: str | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Claim).options(joinedload(Claim.claimant)).filter(
        Claim.claimant_id == current_user.id
    )
    if status:
        query = query.filter(Claim.status == status)
    claims = query.order_by(Claim.created_at.desc()).all()
    unread = message_service.unread_map(
        db, user_id=current_user.id, column=Message.claim_id, thread_ids=[c.id for c in claims]
    )
    return {
        "items": [
            dict(serialize_claim(c), unread_messages=unread.get(c.id, 0)) for c in claims
        ],
        "total": len(claims),
    }


@router.get("/claims/received", summary="Claims on listings owned by the current user")
def list_received_claims(
    status: str | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rows: list[Claim] = []
    for item_type, model in (
        (C.CLAIM_ITEM_FOUND, FoundItem),
        (C.CLAIM_ITEM_LOST, LostItem),
        (C.CLAIM_ITEM_DONATION, Donation),
    ):
        owned_ids = [
            row.id
            for row in db.query(model.id).filter(model.user_id == current_user.id).all()
        ]
        if not owned_ids:
            continue
        query = (
            db.query(Claim)
            .options(joinedload(Claim.claimant))
            .filter(Claim.item_type == item_type, Claim.item_id.in_(owned_ids))
        )
        if status:
            query = query.filter(Claim.status == status)
        rows.extend(query.all())
    rows.sort(key=lambda c: c.created_at or datetime.min, reverse=True)
    unread = message_service.unread_map(
        db, user_id=current_user.id, column=Message.claim_id, thread_ids=[c.id for c in rows]
    )
    return {
        "items": [
            dict(serialize_claim(c), unread_messages=unread.get(c.id, 0)) for c in rows
        ],
        "total": len(rows),
    }


@router.get("/claims/{claim_id}", summary="Claim details (parties and admins only)")
def get_claim(
    claim_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    claim = _load_claim(db, claim_id)
    if not _can_view(db, claim, current_user):
        raise HTTPException(status_code=403, detail="You are not part of this claim")
    return serialize_claim(claim)


@router.post("/claims/{claim_id}/approve", summary="Approve a claim (listing owner / admin)")
def approve_claim(
    claim_id: int,
    review: ClaimReview,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    claim = _load_claim(db, claim_id)
    claim = claim_service.approve_claim(db, claim, current_user, note=review.note)
    return {"message": "Claim approved successfully", "claim": serialize_claim(claim)}


@router.post("/claims/{claim_id}/reject", summary="Reject a claim (listing owner / admin)")
def reject_claim(
    claim_id: int,
    review: ClaimReview,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    claim = _load_claim(db, claim_id)
    claim = claim_service.reject_claim(db, claim, current_user, note=review.note)
    return {"message": "Claim rejected", "claim": serialize_claim(claim)}


@router.post("/claims/{claim_id}/cancel", summary="Cancel your own pending claim")
def cancel_claim(
    claim_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    claim = _load_claim(db, claim_id)
    claim = claim_service.cancel_claim(db, claim, current_user)
    return {"message": "Claim cancelled", "claim": serialize_claim(claim)}


# =========================
# CLAIM CONVERSATIONS (donor/owner <-> requester)
# =========================

def _require_claim_party(db: Session, claim: Claim, user: User) -> None:
    if not _can_view(db, claim, user):
        raise HTTPException(status_code=403, detail="You are not part of this claim")


@router.get("/claims/{claim_id}/messages", summary="Conversation between owner and claimant")
def list_claim_messages(
    claim_id: int,
    page: int = Query(1, ge=1),
    limit: int = Query(100, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    claim = _load_claim(db, claim_id)
    _require_claim_party(db, claim, current_user)
    query = (
        db.query(Message)
        .options(joinedload(Message.sender))
        .filter(Message.claim_id == claim_id)
        .order_by(Message.created_at.asc(), Message.id.asc())
    )
    items, total = paginate(query, page, limit)
    return page_payload([serialize_message(m) for m in items], total, page, limit)


@router.post(
    "/claims/{claim_id}/messages",
    status_code=201,
    summary="Message the other party of a claim (donor <-> acceptor)",
)
def send_claim_message(
    claim_id: int,
    payload: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    claim = _load_claim(db, claim_id)
    _require_claim_party(db, claim, current_user)

    body = payload.body.strip()
    if not body:
        raise HTTPException(status_code=422, detail="Message body cannot be empty")

    item = claim_service.get_claim_item(db, claim.item_type, claim.item_id)
    message = message_service.create_message(
        db, sender_id=current_user.id, claim_id=claim.id, body=body
    )

    # Both sides of the claim (minus the sender) get a deep-linked notice.
    message_service.notify_new_message(
        db,
        sender=current_user,
        recipients={item.user_id, claim.claimant_id},
        body=body,
        context=f"the claim conversation for '{item.name}'",
        related_type=C.RELATED_CLAIM,
        related_id=claim.id,
    )

    return {
        "message": "Message sent",
        "message_id": message.id,
        "claim": serialize_claim(claim),
    }


@router.post("/claims/{claim_id}/messages/read", summary="Mark incoming messages as read")
def read_claim_messages(
    claim_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    claim = _load_claim(db, claim_id)
    _require_claim_party(db, claim, current_user)
    updated = message_service.mark_read(
        db, user_id=current_user.id, column=Message.claim_id, thread_id=claim.id
    )
    return {"message": f"Marked {updated} message(s) as read", "updated": updated}
