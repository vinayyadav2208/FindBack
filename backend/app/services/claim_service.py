"""Claim lifecycle service (MASTER_README §25, §26).

All business rules for claiming found items, answering "I found this" on lost
listings, and requesting donations live here so the HTTP layer stays thin.
AI may later suggest verification questions (§26) but never decides ownership
(§99): every transition below requires a human approve/reject action.
"""

from __future__ import annotations

import logging

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app import constants as C
from app.models import Claim, Donation, FoundItem, LostItem, User
from app.services.notification_service import notify

logger = logging.getLogger("findback.claims")

# status transitions applied to the underlying item on claim creation / review
_ITEM_STATUS_ON_CREATE = {
    C.CLAIM_ITEM_FOUND: C.FOUND_CLAIMED,
    C.CLAIM_ITEM_LOST: C.LOST_CLAIMED,
    C.CLAIM_ITEM_DONATION: C.DONATION_RESERVED,
}
_ITEM_STATUS_ON_APPROVE = {
    C.CLAIM_ITEM_FOUND: C.FOUND_RETURNED,
    C.CLAIM_ITEM_LOST: C.LOST_RESOLVED,
    C.CLAIM_ITEM_DONATION: C.DONATION_CLAIMED,
}
_ITEM_STATUS_ON_REJECT = {
    C.CLAIM_ITEM_FOUND: C.FOUND_ACTIVE,
    C.CLAIM_ITEM_LOST: C.LOST_ACTIVE,
    C.CLAIM_ITEM_DONATION: C.DONATION_AVAILABLE,
}
_ACTIVE_STATUSES = {
    C.CLAIM_ITEM_FOUND: {C.FOUND_ACTIVE, C.FOUND_MATCHED},
    C.CLAIM_ITEM_LOST: {C.LOST_ACTIVE, C.LOST_MATCHED},
    C.CLAIM_ITEM_DONATION: {C.DONATION_AVAILABLE},
}
_OWNER_LABEL = {C.CLAIM_ITEM_FOUND: "found", C.CLAIM_ITEM_LOST: "lost", C.CLAIM_ITEM_DONATION: "donation"}

_MODEL_BY_TYPE = {C.CLAIM_ITEM_FOUND: FoundItem, C.CLAIM_ITEM_LOST: LostItem, C.CLAIM_ITEM_DONATION: Donation}


def get_claim_item(db: Session, item_type: str, item_id: int):
    """Return the underlying item row for a claim, or raise 404."""
    model = _MODEL_BY_TYPE.get(item_type)
    if model is None:
        raise HTTPException(status_code=422, detail=f"Invalid item type '{item_type}'")
    item = db.query(model).filter(model.id == item_id).first()
    if item is None:
        detail = {"FOUND_ITEM": "Found item", "LOST_ITEM": "Lost item", "DONATION": "Donation"}[item_type]
        raise HTTPException(status_code=404, detail=f"{detail} not found")
    return item


def create_claim(
    db: Session,
    *,
    item_type: str,
    item_id: int,
    user: User,
    message: str | None = None,
    verification_answers: dict | None = None,
) -> Claim:
    item = get_claim_item(db, item_type, item_id)

    if item.user_id == user.id:
        raise HTTPException(status_code=400, detail="You cannot claim your own listing")

    if item.status not in _ACTIVE_STATUSES[item_type]:
        raise HTTPException(
            status_code=409,
            detail=f"This listing is no longer available (status: {item.status})",
        )

    duplicate = (
        db.query(Claim)
        .filter(
            Claim.item_type == item_type,
            Claim.item_id == item_id,
            Claim.claimant_id == user.id,
            Claim.status.in_([C.CLAIM_PENDING, C.CLAIM_APPROVED]),
        )
        .first()
    )
    if duplicate:
        raise HTTPException(status_code=409, detail="You already have a claim on this listing")

    claim = Claim(
        item_type=item_type,
        item_id=item_id,
        claimant_id=user.id,
        message=message,
        verification_answers=verification_answers,
        status=C.CLAIM_PENDING,
    )
    item.status = _ITEM_STATUS_ON_CREATE[item_type]
    db.add(claim)
    db.commit()
    db.refresh(claim)

    # Notify the item owner (best effort - never fails the request, §68).
    if item_type == C.CLAIM_ITEM_DONATION:
        notify(
            db,
            user_id=item.user_id,
            type=C.NOTIF_DONATION_CLAIMED,
            title=f"New request for '{item.name}'",
            message=f"{user.name} would like to receive your donation. Review the request to approve or reject it.",
            related_type=C.RELATED_CLAIM,
            related_id=claim.id,
        )
    else:
        notify(
            db,
            user_id=item.user_id,
            type=C.NOTIF_CLAIM_RECEIVED,
            title=f"New claim on '{item.name}'",
            message=f"{user.name} submitted a claim. Review the verification details before deciding.",
            related_type=C.RELATED_CLAIM,
            related_id=claim.id,
        )
    return claim


def _require_reviewer(claim: Claim, item, reviewer: User) -> None:
    if reviewer.role == C.ROLE_ADMIN:
        return
    if item.user_id != reviewer.id:
        raise HTTPException(
            status_code=403,
            detail="Only the listing owner or an admin can review this claim",
        )


def approve_claim(db: Session, claim: Claim, reviewer: User, note: str | None = None) -> Claim:
    item = get_claim_item(db, claim.item_type, claim.item_id)
    _require_reviewer(claim, item, reviewer)
    if claim.status != C.CLAIM_PENDING:
        raise HTTPException(status_code=409, detail=f"Claim is already {claim.status}")

    claim.status = C.CLAIM_APPROVED
    claim.review_note = note
    item.status = _ITEM_STATUS_ON_APPROVE[claim.item_type]
    db.commit()
    db.refresh(claim)

    notify(
        db,
        user_id=claim.claimant_id,
        type=C.NOTIF_CLAIM_APPROVED,
        title=f"Claim approved for '{item.name}'",
        message="Your claim was approved. Coordinate with the owner to collect the item.",
        related_type=C.RELATED_CLAIM,
        related_id=claim.id,
    )
    return claim


def reject_claim(db: Session, claim: Claim, reviewer: User, note: str | None = None) -> Claim:
    item = get_claim_item(db, claim.item_type, claim.item_id)
    _require_reviewer(claim, item, reviewer)
    if claim.status != C.CLAIM_PENDING:
        raise HTTPException(status_code=409, detail=f"Claim is already {claim.status}")

    claim.status = C.CLAIM_REJECTED
    claim.review_note = note
    item.status = _ITEM_STATUS_ON_REJECT[claim.item_type]
    db.commit()
    db.refresh(claim)

    notify(
        db,
        user_id=claim.claimant_id,
        type=C.NOTIF_CLAIM_REJECTED,
        title=f"Claim not approved for '{item.name}'",
        message=note or "The listing owner did not approve your claim.",
        related_type=C.RELATED_CLAIM,
        related_id=claim.id,
    )
    return claim


def cancel_claim(db: Session, claim: Claim, user: User) -> Claim:
    if claim.claimant_id != user.id and user.role != C.ROLE_ADMIN:
        raise HTTPException(status_code=403, detail="Only the claimant can cancel this claim")
    if claim.status != C.CLAIM_PENDING:
        raise HTTPException(status_code=409, detail=f"Claim is already {claim.status}")

    claim.status = C.CLAIM_CANCELLED
    db.commit()
    db.refresh(claim)

    # Release the item back to the marketplace if no other pending claim holds it.
    other_pending = (
        db.query(Claim)
        .filter(
            Claim.item_type == claim.item_type,
            Claim.item_id == claim.item_id,
            Claim.status == C.CLAIM_PENDING,
            Claim.id != claim.id,
        )
        .count()
    )
    if other_pending == 0:
        item = get_claim_item(db, claim.item_type, claim.item_id)
        if item.status == _ITEM_STATUS_ON_CREATE[claim.item_type]:
            item.status = _ITEM_STATUS_ON_REJECT[claim.item_type]
            db.commit()
    return claim
