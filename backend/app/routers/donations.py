"""Donation (free give-away) APIs - MASTER_README §23, §24."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from app import constants as C
from app.dependencies import get_current_user, get_db
from app.models import Claim, Donation, Match, User
from app.schemas import ClaimCreate, DonationCreate, DonationUpdate
from app.services import claim_service
from app.utils.helpers import page_payload, paginate, serialize_donation
from app.utils.query import apply_distance_box_filter, apply_item_filters, within_radius
from app.utils.validators import require_owner_or_admin

router = APIRouter(tags=["Donations"])


def _get_owned(db: Session, donation_id: int, user: User) -> Donation:
    item = db.query(Donation).filter(Donation.id == donation_id).first()
    if item is None:
        raise HTTPException(status_code=404, detail="Donation not found")
    require_owner_or_admin(item.user_id, user)
    return item


@router.get("/donations", summary="List donations (search, filters, pagination)")
def list_donations(
    q: str | None = None,
    category: str | None = None,
    location: str | None = None,
    status: str | None = None,
    condition: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    lat: float | None = None,
    lon: float | None = None,
    radius_km: float | None = Query(None, gt=0),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = db.query(Donation).options(joinedload(Donation.user))
    query = apply_item_filters(
        query, Donation,
        q=q, category=category, location=location, status=status,
        date_from=date_from, date_to=date_to,
    )
    if condition:
        query = query.filter(Donation.condition == condition)

    if lat is not None and lon is not None and radius_km is not None:
        query = apply_distance_box_filter(
            query, Donation, latitude=lat, longitude=lon, radius_km=radius_km
        )
        rows = [r for r in query.all() if within_radius(r, lat, lon, radius_km)]
        total = len(rows)
        items = rows[(page - 1) * limit: page * limit]
    else:
        items, total = paginate(query, page, limit)

    return page_payload([serialize_donation(i) for i in items], total, page, limit)


@router.get("/my-donations", summary="Donations listed by the current user")
def list_my_donations(
    status: str | None = None,
    q: str | None = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Donation).options(joinedload(Donation.user)).filter(
        Donation.user_id == current_user.id
    )
    query = apply_item_filters(query, Donation, q=q, status=status)
    items, total = paginate(query, page, limit)
    return page_payload([serialize_donation(i) for i in items], total, page, limit)


@router.get("/donations/{donation_id}", summary="Donation details")
def get_donation(donation_id: int, db: Session = Depends(get_db)):
    item = db.query(Donation).options(joinedload(Donation.user)).filter(
        Donation.id == donation_id
    ).first()
    if item is None:
        raise HTTPException(status_code=404, detail="Donation not found")
    return serialize_donation(item)


@router.post("/donations", status_code=201, summary="List an item for free")
def create_donation(
    donation_data: DonationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = Donation(
        name=donation_data.name,
        description=donation_data.description,
        category=donation_data.category,
        condition=donation_data.condition,
        location=donation_data.location,
        latitude=donation_data.latitude,
        longitude=donation_data.longitude,
        images=donation_data.images or None,
        user_id=current_user.id,  # from JWT only (§14)
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return {
        "message": "Donation created successfully",
        "donation": serialize_donation(item),
    }


@router.put("/donations/{donation_id}", summary="Update own donation")
def update_donation(
    donation_id: int,
    donation_data: DonationUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = _get_owned(db, donation_id, current_user)
    for field, value in donation_data.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    db.commit()
    db.refresh(item)
    return {
        "message": "Donation updated successfully",
        "donation": serialize_donation(item),
    }


@router.delete("/donations/{donation_id}", summary="Delete own donation")
def delete_donation(
    donation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = _get_owned(db, donation_id, current_user)
    db.query(Claim).filter(
        Claim.item_type == C.CLAIM_ITEM_DONATION, Claim.item_id == item.id
    ).update({"status": C.CLAIM_CANCELLED}, synchronize_session=False)
    db.delete(item)
    db.commit()
    return {"message": "Donation deleted successfully"}


@router.post(
    "/donations/{donation_id}/claim",
    status_code=201,
    summary="Request a donation (creates a claim)",
)
def claim_donation(
    donation_id: int,
    claim_data: ClaimCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    claim = claim_service.create_claim(
        db,
        item_type=C.CLAIM_ITEM_DONATION,
        item_id=donation_id,
        user=current_user,
        message=claim_data.message,
        verification_answers=claim_data.verification_answers,
    )
    return {
        "message": "Donation requested successfully",
        "claim_id": claim.id,
        "status": claim.status,
    }
