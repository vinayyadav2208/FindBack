"""Admin dashboard APIs (MASTER_README §39, §76).

Every route in this router requires the ADMIN role (router-level dependency);
normal users receive 403.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from app import constants as C
from app.dependencies import get_current_user, get_db, require_admin
from app.models import (
    Claim,
    Donation,
    FoundItem,
    LostItem,
    Match,
    Notification,
    Report,
    User,
)
from app.schemas import ReportReview
from app.services import matching_service
from app.services.notification_service import notify
from app.utils.helpers import (
    page_payload,
    paginate,
    serialize_claim,
    serialize_donation,
    serialize_found_item,
    serialize_lost_item,
    serialize_report,
    serialize_user,
)
from app.utils.query import apply_item_filters

router = APIRouter(tags=["Admin"], dependencies=[Depends(require_admin)])


# =========================
# STATISTICS
# =========================

@router.get("/admin/stats", summary="Platform statistics")
def admin_stats(db: Session = Depends(get_db)):
    week_ago = datetime.utcnow() - timedelta(days=7)

    def count(model, *filters):
        query = db.query(func.count(model.id))
        if filters:
            query = query.filter(*filters)
        return query.scalar() or 0

    return {
        "users": {
            "total": count(User),
            "active": count(User, User.is_active.is_(True)),
            "admins": count(User, User.role == C.ROLE_ADMIN),
            "new_last_7_days": count(User, User.created_at >= week_ago),
        },
        "listings": {
            "lost_total": count(LostItem),
            "lost_active": count(LostItem, LostItem.status == C.LOST_ACTIVE),
            "lost_resolved": count(LostItem, LostItem.status == C.LOST_RESOLVED),
            "found_total": count(FoundItem),
            "found_active": count(FoundItem, FoundItem.status == C.FOUND_ACTIVE),
            "found_returned": count(FoundItem, FoundItem.status == C.FOUND_RETURNED),
            "donations_total": count(Donation),
            "donations_available": count(Donation, Donation.status == C.DONATION_AVAILABLE),
        },
        "matches": {
            "total": count(Match),
            "potential": count(Match, Match.status == C.MATCH_POTENTIAL),
            "verified": count(Match, Match.status == C.MATCH_VERIFIED),
            "resolved": count(Match, Match.status == C.MATCH_RESOLVED),
        },
        "claims": {
            "total": count(Claim),
            "pending": count(Claim, Claim.status == C.CLAIM_PENDING),
            "approved": count(Claim, Claim.status == C.CLAIM_APPROVED),
            "rejected": count(Claim, Claim.status == C.CLAIM_REJECTED),
        },
        "reports": {
            "total": count(Report),
            "open": count(Report, Report.status == C.REPORT_OPEN),
            "under_review": count(Report, Report.status == C.REPORT_UNDER_REVIEW),
            "resolved": count(Report, Report.status == C.REPORT_RESOLVED),
        },
        "notifications": {"total": count(Notification)},
    }


# =========================
# USER MANAGEMENT
# =========================

@router.get("/admin/users", summary="List users")
def list_users(
    q: str | None = None,
    role: str | None = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = db.query(User)
    if q:
        term = f"%{q.strip()}%"
        query = query.filter(or_(User.name.like(term), User.email.like(term)))
    if role:
        query = query.filter(User.role == role)
    query = query.order_by(User.created_at.desc())
    items, total = paginate(query, page, limit)
    return page_payload([serialize_user(u) for u in items], total, page, limit)


def _get_user_or_404(db: Session, user_id: int) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.put("/admin/users/{user_id}/suspend", summary="Suspend an account")
def suspend_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user = _get_user_or_404(db, user_id)
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="You cannot suspend your own account")
    user.is_active = False
    db.commit()
    notify(
        db, user_id=user.id, type=C.NOTIF_SYSTEM,
        title="Account suspended",
        message="Your account has been suspended by an administrator. Contact support for details.",
    )
    return {"message": f"User '{user.name}' suspended", "user": serialize_user(user)}


@router.put("/admin/users/{user_id}/activate", summary="Reactivate an account")
def activate_user(user_id: int, db: Session = Depends(get_db)):
    user = _get_user_or_404(db, user_id)
    user.is_active = True
    db.commit()
    notify(
        db, user_id=user.id, type=C.NOTIF_SYSTEM,
        title="Account reactivated",
        message="Your account has been reactivated.",
    )
    return {"message": f"User '{user.name}' activated", "user": serialize_user(user)}


@router.put("/admin/users/{user_id}/role", summary="Change a user's role")
def change_role(
    user_id: int,
    role: str = Query(..., description="USER | ADMIN"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    role = role.strip().upper()
    if role not in C.ROLES:
        raise HTTPException(status_code=422, detail=f"Invalid role. Valid: {', '.join(C.ROLES)}")
    user = _get_user_or_404(db, user_id)
    if user.id == current_user.id and role != C.ROLE_ADMIN:
        raise HTTPException(status_code=400, detail="You cannot demote your own account")
    user.role = role
    db.commit()
    return {"message": f"User '{user.name}' role set to {role}", "user": serialize_user(user)}


# =========================
# LISTINGS MODERATION
# =========================

_LISTING_TYPES = {"LOST": LostItem, "FOUND": FoundItem, "DONATION": Donation}
_SERIALIZERS = {
    "LOST": serialize_lost_item,
    "FOUND": serialize_found_item,
    "DONATION": serialize_donation,
}


@router.get("/admin/listings", summary="Browse all listings across types")
def list_all_listings(
    type: str | None = Query(None, description="LOST | FOUND | DONATION"),
    q: str | None = None,
    status: str | None = None,
    category: str | None = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    wanted = (
        [t for t in (type or "").upper().split(",") if t in _LISTING_TYPES]
        if type else ["LOST", "FOUND", "DONATION"]
    )
    results: list[dict] = []
    total = 0
    for type_name in wanted:
        model = _LISTING_TYPES[type_name]
        query = db.query(model).options(joinedload(model.user))
        query = apply_item_filters(query, model, q=q, status=status, category=category)
        count = query.count()
        total += count
        if not count:
            continue
        offset = max(0, (page - 1) * limit)
        rows = query.order_by(model.created_at.desc()).offset(offset).limit(limit).all()
        results.extend({"type": type_name, **_SERIALIZERS[type_name](row)} for row in rows)
    results.sort(key=lambda item: item.get("created_at") or "", reverse=True)
    return {"items": results[:limit], "total": total, "page": page, "limit": limit}


@router.delete("/admin/listings/{type}/{item_id}", summary="Remove a listing (moderation)")
def delete_listing(
    type: str,
    item_id: int,
    db: Session = Depends(get_db),
):
    type = type.strip().upper()
    model = _LISTING_TYPES.get(type)
    if model is None:
        raise HTTPException(status_code=422, detail=f"Invalid listing type. Valid: {', '.join(_LISTING_TYPES)}")

    item = db.query(model).filter(model.id == item_id).first()
    if item is None:
        raise HTTPException(status_code=404, detail="Listing not found")

    if type == "LOST":
        db.query(Match).filter(Match.lost_item_id == item.id).delete(synchronize_session=False)
        db.query(Claim).filter(Claim.item_type == C.CLAIM_ITEM_LOST, Claim.item_id == item.id).update(
            {"status": C.CLAIM_CANCELLED}, synchronize_session=False
        )
    elif type == "FOUND":
        db.query(Match).filter(Match.found_item_id == item.id).delete(synchronize_session=False)
        db.query(Claim).filter(Claim.item_type == C.CLAIM_ITEM_FOUND, Claim.item_id == item.id).update(
            {"status": C.CLAIM_CANCELLED}, synchronize_session=False
        )
    else:
        db.query(Claim).filter(Claim.item_type == C.CLAIM_ITEM_DONATION, Claim.item_id == item.id).update(
            {"status": C.CLAIM_CANCELLED}, synchronize_session=False
        )

    owner_id, item_name = item.user_id, item.name
    db.delete(item)
    db.commit()

    notify(
        db, user_id=owner_id, type=C.NOTIF_SYSTEM,
        title=f"Your listing '{item_name}' was removed",
        message="An administrator removed this listing after a moderation review.",
    )
    return {"message": f"{type} listing #{item_id} removed"}


# =========================
# CLAIMS & REPORTS REVIEW
# =========================

@router.get("/admin/claims", summary="All claims")
def list_all_claims(
    status: str | None = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = db.query(Claim).options(joinedload(Claim.claimant))
    if status:
        query = query.filter(Claim.status == status)
    query = query.order_by(Claim.created_at.desc())
    items, total = paginate(query, page, limit)
    return page_payload([serialize_claim(c) for c in items], total, page, limit)


@router.get("/admin/reports", summary="Report review queue")
def list_reports(
    status: str | None = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = db.query(Report)
    if status:
        query = query.filter(Report.status == status)
    query = query.order_by(Report.created_at.desc())
    items, total = paginate(query, page, limit)
    return page_payload([serialize_report(r) for r in items], total, page, limit)


@router.put("/admin/reports/{report_id}", summary="Review a report (set status)")
def review_report(
    report_id: int,
    review: ReportReview,
    db: Session = Depends(get_db),
):
    report = db.query(Report).filter(Report.id == report_id).first()
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    report.status = review.status
    db.commit()
    if review.status in (C.REPORT_RESOLVED, C.REPORT_DISMISSED):
        notify(
            db, user_id=report.reporter_id, type=C.NOTIF_SYSTEM,
            title=f"Your report was {review.status.lower().replace('_', ' ')}",
            message="Thank you for helping keep FindBack safe.",
        )
    return {"message": "Report updated", "report": serialize_report(report)}


# =========================
# GLOBAL AI RETRY
# =========================

@router.post("/admin/matches/rebuild", summary="Run AI matching across all active listings")
def rebuild_all_matches(db: Session = Depends(get_db)):
    created = 0
    lost_ids = [
        row[0] for row in db.query(LostItem.id)
        .filter(LostItem.status.in_([C.LOST_ACTIVE, C.LOST_MATCHED]))
        .all()
    ]
    found_ids = [
        row[0] for row in db.query(FoundItem.id)
        .filter(FoundItem.status.in_([C.FOUND_ACTIVE, C.FOUND_MATCHED]))
        .all()
    ]
    for item_id in lost_ids:
        created += len(matching_service.find_matches(db, "LOST", item_id))
    for item_id in found_ids:
        created += len(matching_service.find_matches(db, "FOUND", item_id))
    return {"message": "Global matching run complete", "new_matches": created}
