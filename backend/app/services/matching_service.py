"""Lost <-> found matching engine (MASTER_README §27, §30, §31, §34).

Pipeline:  item text -> embeddings -> vector index -> candidate retrieval
           -> combined scoring (text/image/location/category) -> Match rows
           -> notifications for newly found matches.

Scores are *rankings*, never proof of ownership (§31): AI only suggests,
explains and ranks - humans approve claims (§99). If any AI component fails,
matching logs the error and the listings remain untouched (§68).
"""

from __future__ import annotations

import logging
import math

from sqlalchemy.orm import Session

from app import constants as C
from app.config import settings
from app.models import FoundItem, LostItem, Match
from app.services import embedding_service, image_service
from app.services.notification_service import notify
from app.utils.helpers import haversine_km

logger = logging.getLogger("findback.matching")

_SOURCE_MODELS = {"LOST": LostItem, "FOUND": FoundItem}
_CANDIDATE_MODELS = {"LOST": FoundItem, "FOUND": LostItem}
_MATCHABLE_STATUSES = {
    "LOST": (C.LOST_ACTIVE, C.LOST_MATCHED),
    "FOUND": (C.FOUND_ACTIVE, C.FOUND_MATCHED),
}
_MARK_MATCHED = {"LOST": C.LOST_MATCHED, "FOUND": C.FOUND_MATCHED}
_ACTIVE = {"LOST": C.LOST_ACTIVE, "FOUND": C.FOUND_ACTIVE}


def _location_score(a, b) -> float:
    if None not in (a.latitude, a.longitude, b.latitude, b.longitude):
        distance = haversine_km(a.latitude, a.longitude, b.latitude, b.longitude)
        # smooth decay: ~0.72 at 10km, ~0.37 at 25km, ~0.05 at 75km
        return math.exp(-distance / 25.0)
    la = (a.location or "").strip().lower()
    lb = (b.location or "").strip().lower()
    if la and la == lb:
        return 1.0
    ta, tb = set(la.split()), set(lb.split())
    if ta and tb and (ta & tb):
        return 0.6  # shares a place token ("jntu", "hyderabad", ...)
    return 0.0


def _category_score(a, b) -> float:
    ca = (getattr(a, "category", "") or "").strip().lower()
    cb = (getattr(b, "category", "") or "").strip().lower()
    if not ca or not cb:
        return 0.0
    return 1.0 if ca == cb else 0.0


def _combined_score(text: float, image: float | None, location: float, category: float) -> float:
    weights = {
        "text": settings.W_TEXT,
        "image": settings.W_IMAGE,
        "location": settings.W_LOCATION,
        "category": settings.W_CATEGORY,
    }
    scores = {"text": text, "image": image, "location": location, "category": category}
    if image is None:
        # No image evidence available: drop that weight and renormalize so
        # text/location/category evidence is not unfairly penalized (§31).
        weights.pop("image", None)
        scores.pop("image", None)
    total_weight = sum(weights.values()) or 1.0
    return sum(weights[k] * (scores[k] or 0.0) for k in weights) / total_weight


def _confidence_label(combined: float) -> str:
    if combined >= 0.75:
        return "Strong potential match"
    if combined >= 0.55:
        return "Potential match"
    return "Possible match"


def _build_explanation(
    source, candidate, text: float, image: float | None, location: float,
    category: float, combined: float,
) -> dict:
    reasons: list[str] = []
    if text >= 0.6:
        reasons.append("Similar wording in name and description")
    elif text >= 0.35:
        reasons.append("Some similar wording in the description")
    if category >= 1.0:
        reasons.append(f"Same category ({source.category})")
    if location >= 0.95:
        reasons.append(f"Same location ({source.location})")
    elif location >= 0.5:
        reasons.append("Locations are close to each other")
    if image is not None and image >= 0.7:
        reasons.append("Photos look similar")
    if not reasons:
        reasons.append("Some overlap in searchable details")

    return {
        "reasons": reasons,
        "confidence": _confidence_label(combined),
        "confidence_note": (
            "AI confidence: this is a potential match only. "
            "Verify ownership before returning or claiming any item."
        ),
    }


def find_matches(
    db: Session,
    item_type: str,
    item_id: int,
    *,
    top_k: int | None = None,
    min_score: float | None = None,
    notify_users: bool = True,
) -> list[Match]:
    """Find and persist potential matches for one lost or found item."""
    item_type = item_type.upper()
    if item_type not in _SOURCE_MODELS:
        raise ValueError(f"Invalid item type {item_type!r}")

    source_model = _SOURCE_MODELS[item_type]
    candidate_model = _CANDIDATE_MODELS[item_type]
    top_k = top_k or settings.MATCH_TOP_K
    min_score = settings.MATCH_MIN_SCORE if min_score is None else min_score

    source = db.query(source_model).filter(source_model.id == item_id).first()
    if source is None:
        return []
    if source.status not in _MATCHABLE_STATUSES[item_type]:
        return []  # resolved/cancelled/claimed items are not re-matched

    candidates = (
        db.query(candidate_model)
        .filter(candidate_model.status.in_(_MATCHABLE_STATUSES["FOUND" if item_type == "LOST" else "LOST"]))
        .all()
    )
    if not candidates:
        return []

    # 1) embed source + candidates, 2) retrieve candidates via the vector index
    from app.services.vector_store import create_index

    index = create_index()
    source_vector = embedding_service.embed_item(source)
    for candidate in candidates:
        index.add(str(candidate.id), embedding_service.embed_item(candidate))

    retrieved = index.search(source_vector, top_k=max(top_k, 1))

    results: list[Match] = []
    for candidate_id_raw, _retrieval_score in retrieved:
        candidate = next((c for c in candidates if str(c.id) == candidate_id_raw), None)
        if candidate is None:
            continue

        text = embedding_service.cosine(
            source_vector, embedding_service.embed_item(candidate)
        )
        category = _category_score(source, candidate)
        location = _location_score(source, candidate)
        image = image_service.similarity(source, candidate)
        combined = _combined_score(text, image, location, category)
        if combined < min_score:
            continue

        if item_type == "LOST":
            lost_item_id, found_item_id = source.id, candidate.id
            kind_pairs = (("LOST", source), ("FOUND", candidate))
        else:
            lost_item_id, found_item_id = candidate.id, source.id
            kind_pairs = (("FOUND", source), ("LOST", candidate))

        existing = (
            db.query(Match)
            .filter(
                Match.lost_item_id == lost_item_id,
                Match.found_item_id == found_item_id,
            )
            .first()
        )
        explanation = _build_explanation(source, candidate, text, image, location, category, combined)

        if existing is None:
            match = Match(
                lost_item_id=lost_item_id,
                found_item_id=found_item_id,
                text_score=round(text, 4),
                image_score=round(image, 4) if image is not None else 0.0,
                location_score=round(location, 4),
                category_score=round(category, 4),
                combined_score=round(combined, 4),
                explanation=explanation,
                status=C.MATCH_POTENTIAL,
            )
            db.add(match)
            results.append(match)
            db.flush()  # assign id

            # mark both sides MATCHED while still ACTIVE (display state only)
            for kind, item in kind_pairs:
                if item.status == _ACTIVE[kind]:
                    item.status = _MARK_MATCHED[kind]

            if notify_users:
                confidence = explanation["confidence"]
                _notify_match(db, source, candidate, confidence, item_type)
                _notify_match(
                    db, candidate, source, confidence,
                    "FOUND" if item_type == "LOST" else "LOST",
                )
        else:
            existing.text_score = round(text, 4)
            existing.image_score = round(image, 4) if image is not None else existing.image_score
            existing.location_score = round(location, 4)
            existing.category_score = round(category, 4)
            existing.combined_score = round(combined, 4)
            existing.explanation = explanation

    db.commit()
    for match in results:
        db.refresh(match)
    return results


def _notify_match(db: Session, item, other, confidence: str, item_type: str) -> None:
    kind = "lost" if item_type == "LOST" else "found"
    other_kind = "found" if item_type == "LOST" else "lost"
    notify(
        db,
        user_id=item.user_id,
        type=C.NOTIF_MATCH_FOUND,
        title=f"Potential {other_kind} item match for '{item.name}'",
        message=(
            f"{confidence}: a {other_kind} listing ('{other.name}') looks similar to your "
            f"lost {kind} item report. {other.location}. Open Matches to review why - "
            "always verify ownership before arranging a handover."
        ),
    )


def run_matching_background(item_type: str, item_id: int) -> None:
    """BackgroundTasks entry point: owns its own DB session (§67)."""
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        find_matches(db, item_type, item_id)
    except Exception:
        logger.exception(
            "Background matching failed for %s #%s (listing remains available)",
            item_type, item_id,
        )
        db.rollback()
    finally:
        db.close()


def run_for_user(db: Session, user) -> dict:
    """Manual retry: run matching across the user's own active listings."""
    created = 0
    for item in (
        db.query(LostItem)
        .filter(LostItem.user_id == user.id, LostItem.status.in_(_MATCHABLE_STATUSES["LOST"]))
        .all()
    ):
        created += len(find_matches(db, "LOST", item.id, notify_users=True))
    for item in (
        db.query(FoundItem)
        .filter(FoundItem.user_id == user.id, FoundItem.status.in_(_MATCHABLE_STATUSES["FOUND"]))
        .all()
    ):
        created += len(find_matches(db, "FOUND", item.id, notify_users=True))
    return {"new_matches": created}
