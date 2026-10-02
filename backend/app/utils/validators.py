"""Input validation / normalization helpers shared across routers."""

from __future__ import annotations

import re

from fastapi import HTTPException

# Characters that would break MySQL LIKE searches are escaped with a backslash.
LIKE_SPECIAL = re.compile(r"([\\%_])")


def clean_search_query(q: str | None, max_length: int = 200) -> str:
    if not q:
        return ""
    q = " ".join(str(q).split())  # collapse whitespace
    return q[:max_length]


def to_like_term(term: str) -> str:
    """Escape LIKE wildcards in a user-supplied term."""
    return f"%{LIKE_SPECIAL.sub(r"\\\1", term)}%"


def require_owner_or_admin(item_owner_id: int, current_user) -> None:
    """Ownership check (§14): the acting user must own the resource or be admin."""
    if current_user.role == "ADMIN":
        return
    if item_owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="You do not own this resource")


def ensure_coordinates(latitude, longitude) -> None:
    if latitude is not None and not -90 <= float(latitude) <= 90:
        raise HTTPException(status_code=422, detail="latitude must be between -90 and 90")
    if longitude is not None and not -180 <= float(longitude) <= 180:
        raise HTTPException(status_code=422, detail="longitude must be between -180 and 180")
