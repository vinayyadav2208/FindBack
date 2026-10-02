"""Global search, nearby items and public statistics (MASTER_README §19, §22).

GET /search  - keyword search across lost, found and donation listings
GET /nearby  - distance-sorted listings around a coordinate
GET /stats   - aggregate counts for the home page
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session, joinedload

from app import constants as C
from app.dependencies import get_db
from app.models import Donation, FoundItem, LostItem, User
from app.utils.helpers import haversine_km, serialize_donation, serialize_found_item, serialize_lost_item
from app.utils.query import apply_item_filters, apply_distance_box_filter
from app.utils.validators import clean_search_query, to_like_term

router = APIRouter(tags=["Search"])

_SERIALIZERS = {
    "LOST": serialize_lost_item,
    "FOUND": serialize_found_item,
    "DONATION": serialize_donation,
}
_MODELS = {"LOST": LostItem, "FOUND": FoundItem, "DONATION": Donation}


def _parse_types(type_filter: str | None) -> list[str]:
    if not type_filter:
        return ["LOST", "FOUND", "DONATION"]
    wanted = [t.strip().upper() for t in type_filter.split(",") if t.strip()]
    valid = [t for t in wanted if t in _MODELS]
    return valid or ["LOST", "FOUND", "DONATION"]


@router.get("/search", summary="Global keyword search across all listing types")
def search(
    q: str = Query(..., min_length=1, description="Search query"),
    type: str | None = Query(None, description="Comma list: LOST,FOUND,DONATION"),
    category: str | None = None,
    location: str | None = None,
    status: str | None = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    term = clean_search_query(q)
    results: list[dict] = []
    total = 0

    for type_name in _parse_types(type):
        model = _MODELS[type_name]
        query = db.query(model).options(joinedload(model.user))
        query = apply_item_filters(
            query, model, q=term, category=category, location=location, status=status
        )
        count = query.count()
        if not count:
            continue
        total += count
        offset = max(0, (page - 1) * limit)
        rows = query.order_by(model.created_at.desc()).offset(offset).limit(limit).all()
        serializer = _SERIALIZERS[type_name]
        results.extend(
            {"type": type_name, **serializer(row)} for row in rows
        )

    results.sort(key=lambda item: item.get("created_at") or "", reverse=True)
    return {
        "items": results[:limit],
        "total": total,
        "page": page,
        "limit": limit,
        "query": term,
    }


@router.get("/nearby", summary="Listings near a coordinate, distance sorted")
def nearby(
    lat: float = Query(..., description="Centre latitude"),
    lon: float = Query(..., description="Centre longitude"),
    radius_km: float = Query(10, gt=0, le=200),
    type: str | None = Query(None, description="Comma list: LOST,FOUND,DONATION"),
    category: str | None = None,
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    results: list[dict] = []
    for type_name in _parse_types(type):
        model = _MODELS[type_name]
        query = db.query(model).options(joinedload(model.user))
        query = apply_item_filters(query, model, category=category)
        query = apply_distance_box_filter(
            query, model, latitude=lat, longitude=lon, radius_km=radius_km
        )
        serializer = _SERIALIZERS[type_name]
        for row in query.all():
            if row.latitude is None or row.longitude is None:
                continue
            distance = haversine_km(lat, lon, row.latitude, row.longitude)
            if distance <= radius_km:
                results.append(
                    {"type": type_name, "distance_km": round(distance, 2), **serializer(row)}
                )

    results.sort(key=lambda item: item["distance_km"])
    return {
        "items": results[:limit],
        "total": len(results),
        "center": {"lat": lat, "lon": lon},
        "radius_km": radius_km,
    }


@router.get("/stats", summary="Public platform statistics for the home page")
def stats(db: Session = Depends(get_db)):
    def count(model, *filters):
        return db.query(model).filter(*filters).count() if filters else db.query(model).count()

    return {
        "users": count(User),
        "lost_items": count(LostItem),
        "lost_active": count(LostItem, LostItem.status == C.LOST_ACTIVE),
        "lost_resolved": count(LostItem, LostItem.status == C.LOST_RESOLVED),
        "found_items": count(FoundItem),
        "found_active": count(FoundItem, FoundItem.status == C.FOUND_ACTIVE),
        "found_returned": count(FoundItem, FoundItem.status == C.FOUND_RETURNED),
        "donations": count(Donation),
        "donations_available": count(Donation, Donation.status == C.DONATION_AVAILABLE),
    }
