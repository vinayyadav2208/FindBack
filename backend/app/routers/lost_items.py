"""Lost item CRUD, listing, search and filters (MASTER_README §17).

Ownership always comes from the JWT (§14) - payloads never accept user_id.
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from app import constants as C
from app.dependencies import get_current_user, get_db
from app.models import Claim, LostItem, Match, User
from app.schemas import LostItemCreate, LostItemUpdate
from app.services.matching_service import run_matching_background
from app.utils.helpers import clamp_pagination, page_payload, paginate, serialize_lost_item
from app.utils.query import apply_distance_box_filter, apply_item_filters, within_radius
from app.utils.validators import require_owner_or_admin

router = APIRouter(tags=["Lost Items"])


def _get_owned_item(db: Session, item_id: int, user: User) -> LostItem:
    item = db.query(LostItem).filter(LostItem.id == item_id).first()
    if item is None:
        raise HTTPException(status_code=404, detail="Lost item not found")
    require_owner_or_admin(item.user_id, user)
    return item


@router.get("/lost-items", summary="List lost items (search, filters, pagination)")
def list_lost_items(
    q: str | None = Query(None, description="Keyword search over name/description/location/category"),
    category: str | None = Query(None, description="Exact category, e.g. Wallet"),
    location: str | None = Query(None, description="Location substring, e.g. Hyderabad"),
    status: str | None = Query(None, description="ACTIVE | MATCHED | CLAIMED | RESOLVED | CANCELLED"),
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    lat: float | None = Query(None, description="Centre latitude for distance filtering"),
    lon: float | None = Query(None, description="Centre longitude for distance filtering"),
    radius_km: float | None = Query(None, gt=0, description="Radius in km (requires lat & lon)"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = db.query(LostItem).options(joinedload(LostItem.user))
    query = apply_item_filters(
        query, LostItem,
        q=q, category=category, location=location, status=status,
        date_from=date_from, date_to=date_to,
    )

    if lat is not None and lon is not None and radius_km is not None:
        query = apply_distance_box_filter(
            query, LostItem, latitude=lat, longitude=lon, radius_km=radius_km
        )
        rows = [r for r in query.all() if within_radius(r, lat, lon, radius_km)]
        total = len(rows)
        items = rows[(page - 1) * limit: page * limit]
    else:
        items, total = paginate(query, page, limit)

    return page_payload([serialize_lost_item(i) for i in items], total, page, limit)


@router.get("/my-lost-items", summary="Lost items reported by the current user")
def list_my_lost_items(
    status: str | None = None,
    q: str | None = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(LostItem).options(joinedload(LostItem.user)).filter(
        LostItem.user_id == current_user.id
    )
    query = apply_item_filters(query, LostItem, q=q, status=status)
    items, total = paginate(query, page, limit)
    return page_payload([serialize_lost_item(i) for i in items], total, page, limit)


@router.get("/lost-items/{item_id}", summary="Lost item details")
def get_lost_item(item_id: int, db: Session = Depends(get_db)):
    item = db.query(LostItem).options(joinedload(LostItem.user)).filter(
        LostItem.id == item_id
    ).first()
    if item is None:
        raise HTTPException(status_code=404, detail="Lost item not found")
    return serialize_lost_item(item)


@router.post("/lost-items", status_code=201, summary="Report a lost item")
def create_lost_item(
    item_data: LostItemCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = LostItem(
        name=item_data.name,
        description=item_data.description,
        category=item_data.category,
        location=item_data.location,
        latitude=item_data.latitude,
        longitude=item_data.longitude,
        images=item_data.images or None,
        user_id=current_user.id,  # always from JWT, never from the payload
    )
    db.add(item)
    db.commit()
    db.refresh(item)

    # AI matching runs in the background; failures never affect the listing (§68).
    background_tasks.add_task(run_matching_background, "LOST", item.id)

    return {
        "message": "Lost item created successfully",
        "item_id": item.id,
        "name": item.name,
        "description": item.description,
        "category": item.category,
        "location": item.location,
        "status": item.status,
        "user_id": item.user_id,
        "user_name": current_user.name,
        "created_at": item.created_at.isoformat() if item.created_at else None,
    }


@router.put("/lost-items/{item_id}", summary="Update own lost item")
def update_lost_item(
    item_id: int,
    item_data: LostItemUpdate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = _get_owned_item(db, item_id, current_user)
    updates = item_data.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(item, field, value)
    db.commit()
    db.refresh(item)

    # Re-run matching when meaningful fields changed (§66: not on every view).
    if {"name", "description", "category", "location"} & set(updates):
        background_tasks.add_task(run_matching_background, "LOST", item.id)

    return {
        "message": "Lost item updated successfully",
        "item": serialize_lost_item(item),
    }


@router.delete("/lost-items/{item_id}", summary="Delete own lost item")
def delete_lost_item(
    item_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = _get_owned_item(db, item_id, current_user)

    # Remove dependent derived data so the delete cannot fail on FK constraints.
    db.query(Match).filter(Match.lost_item_id == item.id).delete(synchronize_session=False)
    db.query(Claim).filter(
        Claim.item_type == C.CLAIM_ITEM_LOST, Claim.item_id == item.id
    ).update({"status": C.CLAIM_CANCELLED}, synchronize_session=False)
    db.delete(item)
    db.commit()

    return {"message": "Lost item deleted successfully"}
