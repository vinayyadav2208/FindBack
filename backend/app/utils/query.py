"""Listing query filters shared by lost / found / donation listings.

Filters run at database level (§20) except distance, which uses a SQL
bounding-box pre-filter followed by an exact Haversine check in Python.
"""

from __future__ import annotations

import math

from sqlalchemy import or_
from sqlalchemy.orm import Query

from app.utils.helpers import haversine_km
from app.utils.validators import clean_search_query, to_like_term

# Approximation used for the SQL bounding box.
DEG_LAT_KM = 111.0


def apply_item_filters(
    query: Query,
    model,
    *,
    q: str | None = None,
    category: str | None = None,
    location: str | None = None,
    status: str | None = None,
    date_from=None,
    date_to=None,
) -> Query:
    """Apply keyword + facet filters entirely inside the database."""
    term = clean_search_query(q)
    if term:
        for word in term.split():  # every word must match at least one field
            like = to_like_term(word)
            query = query.filter(
                or_(
                    model.name.like(like),
                    model.description.like(like),
                    model.location.like(like),
                    model.category.like(like),
                )
            )
    if category:
        query = query.filter(model.category == category)
    if location:
        query = query.filter(model.location.like(to_like_term(location.strip())))
    if status:
        query = query.filter(model.status == status)
    if date_from:
        query = query.filter(model.created_at >= date_from)
    if date_to:
        query = query.filter(model.created_at <= date_to)
    return query


def apply_distance_box_filter(
    query: Query,
    model,
    *,
    latitude: float,
    longitude: float,
    radius_km: float,
) -> Query:
    """Cheap SQL bounding box around the point; exact filtering happens later."""
    delta_lat = radius_km / DEG_LAT_KM
    cos_lat = max(abs(math.cos(math.radians(latitude))), 0.01)
    delta_lon = radius_km / (DEG_LAT_KM * cos_lat)
    return (
        query.filter(model.latitude.isnot(None))
        .filter(model.longitude.isnot(None))
        .filter(model.latitude.between(latitude - delta_lat, latitude + delta_lat))
        .filter(model.longitude.between(longitude - delta_lon, longitude + delta_lon))
    )


def within_radius(item, latitude: float, longitude: float, radius_km: float) -> bool:
    if item.latitude is None or item.longitude is None:
        return False
    return (
        haversine_km(latitude, longitude, item.latitude, item.longitude) <= radius_km
    )
