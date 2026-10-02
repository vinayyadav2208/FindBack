"""Found item CRUD, listing, search and filters (MASTER_README §18)."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from app import constants as C
from app.dependencies import get_current_user, get_db
from app.models import Claim, FoundItem, Match, User
from app.schemas import FoundItemCreate, FoundItemUpdate
from app.utils.helpers import page_payload, paginate, serialize_found_item
from app.utils.query import apply_distance_box_filter, apply_item_filters, within_radius
from app.utils.validators import require_owner_or_admin

router = APIRouter(tags=["Found Items"])


def _get_owned_item(db: Session, item_id: int, user: User) -> FoundItem:
    item = db.query(FoundItem).filter(FoundItem.id == item_id).first()
    if item is None:
        raise HTTPException(status_code=404, detail="Found item not found")
    require_owner_or_admin(item.user_id, user)
    return item


@router.get("/found-items", summary="List found items (search, filters, pagination)")
def list_found_items(
    q: str | None = Query(None, description="Keyword search over name/description/location/category"),
    category: str | None = None,
    location: str | None = None,
    status: str | None = Query(None, description="ACTIVE | MATCHED | CLAIMED | RETURNED | CANCELLED"),
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    lat: float | None = None,
    lon: float | None = None,
    radius_km: float | None = Query(None, gt=0),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = db.query(FoundItem).options(joinedload(FoundItem.user))
    query = apply_item_filters(
        query, FoundItem,
        q=q, category=category, location=location, status=status,
        date_from=date_from, date_to=date_to,
    )

    if lat is not None and lon is not None and radius_km is not None:
        query = apply_distance_box_filter(
            query, FoundItem, latitude=lat, longitude=lon, radius_km=radius_km
        )
        rows = [r for r in query.all() if within_radius(r, lat, lon, radius_km)]
        total = len(rows)
        items = rows[(page - 1) * limit: page * limit]
    else:
        items, total = paginate(query, page, limit)

    return page_payload([serialize_found_item(i) for i in items], total, page, limit)


@router.get("/my-found-items", summary="Found items reported by the current user")
def list_my_found_items(
    status: str | None = None,
    q: str | None = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(FoundItem).options(joinedload(FoundItem.user)).filter(
        FoundItem.user_id == current_user.id
    )
    query = apply_item_filters(query, FoundItem, q=q, status=status)
    items, total = paginate(query, page, limit)
    return page_payload([serialize_found_item(i) for i in items], total, page, limit)


@router.get("/found-items/{item_id}", summary="Found item details")
def get_found_item(item_id: int, db: Session = Depends(get_db)):
    item = db.query(FoundItem).options(joinedload(FoundItem.user)).filter(
        FoundItem.id == item_id
    ).first()
    if item is None:
        raise HTTPException(status_code=404, detail="Found item not found")
    return serialize_found_item(item)


@router.post("/found-items", status_code=201, summary="Report a found item")
def create_found_item(
    item_data: FoundItemCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = FoundItem(
        name=item_data.name,
        description=item_data.description,
        category=item_data.category,
        location=item_data.location,
        latitude=item_data.latitude,
        longitude=item_data.longitude,
        images=item_data.images or None,
        user_id=current_user.id,
    )
    db.add(item)
    db.commit()
    db.refresh(item)

    return {
        "message": "Found item created successfully",
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


@router.put("/found-items/{item_id}", summary="Update own found item")
def update_found_item(
    item_id: int,
    item_data: FoundItemUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = _get_owned_item(db, item_id, current_user)
    updates = item_data.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(item, field, value)
    db.commit()
    db.refresh(item)
    return {
        "message": "Found item updated successfully",
        "item": serialize_found_item(item),
    }


@router.delete("/found-items/{item_id}", summary="Delete own found item")
def delete_found_item(
    item_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = _get_owned_item(db, item_id, current_user)

    db.query(Match).filter(Match.found_item_id == item.id).delete(synchronize_session=False)
    db.query(Claim).filter(
        Claim.item_type == C.CLAIM_ITEM_FOUND, Claim.item_id == item.id
    ).update({"status": C.CLAIM_CANCELLED}, synchronize_session=False)
    db.delete(item)
    db.commit()

    return {"message": "Found item deleted successfully"}
