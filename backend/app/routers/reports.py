"""Reporting APIs (MASTER_README §38).

Users can report fake listings, scams, inappropriate content, duplicates or
suspicious behaviour. Reports go to the admin review queue; reporters can
follow their own reports.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import constants as C
from app.dependencies import get_current_user, get_db
from app.models import Donation, FoundItem, LostItem, Report, User
from app.schemas import ReportCreate
from app.services.notification_service import notify
from app.utils.helpers import serialize_report

router = APIRouter(tags=["Reports"])

_TARGET_MODELS = {
    C.REPORT_TARGET_LOST: LostItem,
    C.REPORT_TARGET_FOUND: FoundItem,
    C.REPORT_TARGET_DONATION: Donation,
    C.REPORT_TARGET_USER: User,
}


def _notify_admins(db: Session, report: Report) -> None:
    admins = db.query(User).filter(User.role == C.ROLE_ADMIN, User.is_active.is_(True)).all()
    for admin in admins:
        if admin.id == report.reporter_id:
            continue
        notify(
            db,
            user_id=admin.id,
            type=C.NOTIF_LISTING_REPORTED,
            title=f"New report: {report.reason.replace('_', ' ').title()}",
            message=f"A {report.target_type} listing was reported. Review it in the admin dashboard.",
            related_type=C.RELATED_REPORT,
            related_id=report.id,
        )


@router.post("/reports", status_code=201, summary="Report a listing or user")
def create_report(
    report_data: ReportCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    model = _TARGET_MODELS[report_data.target_type]
    target = db.query(model).filter(model.id == report_data.target_id).first()
    if target is None:
        raise HTTPException(status_code=404, detail="Report target not found")

    if report_data.target_type == C.REPORT_TARGET_USER and target.id == current_user.id:
        raise HTTPException(status_code=400, detail="You cannot report yourself")

    duplicate = (
        db.query(Report)
        .filter(
            Report.reporter_id == current_user.id,
            Report.target_type == report_data.target_type,
            Report.target_id == report_data.target_id,
            Report.status.in_([C.REPORT_OPEN, C.REPORT_UNDER_REVIEW]),
        )
        .first()
    )
    if duplicate:
        raise HTTPException(status_code=409, detail="You already reported this target")

    report = Report(
        reporter_id=current_user.id,  # from JWT (§14)
        target_type=report_data.target_type,
        target_id=report_data.target_id,
        reason=report_data.reason,
        description=report_data.description,
        status=C.REPORT_OPEN,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    _notify_admins(db, report)

    return {"message": "Report submitted. Our team will review it.", "report": serialize_report(report)}


@router.get("/reports/mine", summary="Reports I submitted")
def list_my_reports(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    reports = (
        db.query(Report)
        .filter(Report.reporter_id == current_user.id)
        .order_by(Report.created_at.desc())
        .all()
    )
    return {"items": [serialize_report(r) for r in reports], "total": len(reports)}
