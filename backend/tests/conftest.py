"""Pytest bootstrap for the FindBack backend.

Environment overrides are applied BEFORE any `app.*` module is imported, so
every test runs against the dedicated `findback_test` database - never against
the development data in `findback` (MASTER_README §92). Rate limiting is
disabled for functional tests (its logic is unit-tested separately) and
uploads go to an isolated media directory.
"""

from __future__ import annotations

import os
import sys
import uuid
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def _configured_database_url() -> str:
    """DATABASE_URL from the process environment, or from backend/.env."""
    if os.environ.get("DATABASE_URL"):
        return os.environ["DATABASE_URL"]
    env_file = BACKEND_DIR / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("DATABASE_URL="):
                return line.partition("=")[2].strip().strip('"').strip("'")
    raise RuntimeError("DATABASE_URL is not configured (set it or backend/.env)")


# Swap only the database name: findback -> findback_test
os.environ["DATABASE_URL"] = _configured_database_url().rsplit("/", 1)[0] + "/findback_test"
os.environ["RATE_LIMIT_ENABLED"] = "false"
os.environ["MEDIA_DIR"] = str(BACKEND_DIR / "media_test")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import constants as C  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.models import (  # noqa: E402
    Claim,
    Donation,
    FoundItem,
    LostItem,
    Match,
    Message,
    Notification,
    Report,
    User,
)


@pytest.fixture(scope="session")
def client():
    """Application client; entering the fixture runs the lifespan (schema sync)."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def register(client):
    """Register a fresh user; returns (auth_headers, user_dict)."""

    def _register() -> tuple[dict, dict]:
        tag = uuid.uuid4().hex[:10]
        email = f"pytest-{tag}@pytest.local"
        response = client.post(
            "/auth/register",
            json={"name": f"user-{tag}", "email": email, "password": "Str0ngPass!xyz"},
        )
        assert response.status_code == 201, response.text
        headers = {"Authorization": f"Bearer {response.json()['access_token']}"}
        me = client.get("/me", headers=headers)
        assert me.status_code == 200, me.text
        return headers, me.json()

    return _register


@pytest.fixture
def user(register):
    headers, user = register()
    return headers


@pytest.fixture
def admin(register):
    """Registered user promoted to ADMIN directly in the test database."""
    headers, user = register()
    db = SessionLocal()
    try:
        row = db.query(User).filter(User.id == user["id"]).first()
        row.role = C.ROLE_ADMIN
        db.commit()
    finally:
        db.close()
    return headers


def _purge_user(db, user: User) -> None:
    db.query(Claim).filter(Claim.claimant_id == user.id).delete(synchronize_session=False)
    for model, match_column, claim_type in (
        (LostItem, Match.lost_item_id, C.CLAIM_ITEM_LOST),
        (FoundItem, Match.found_item_id, C.CLAIM_ITEM_FOUND),
    ):
        for item in db.query(model).filter(model.user_id == user.id).all():
            match_ids = [
                row[0] for row in db.query(Match.id).filter(match_column == item.id).all()
            ]
            if match_ids:
                db.query(Message).filter(Message.match_id.in_(match_ids)).delete(
                    synchronize_session=False
                )
            db.query(Match).filter(match_column == item.id).delete(synchronize_session=False)
            db.query(Claim).filter(
                Claim.item_type == claim_type, Claim.item_id == item.id
            ).delete(synchronize_session=False)
            db.delete(item)
    for item in db.query(Donation).filter(Donation.user_id == user.id).all():
        db.query(Claim).filter(
            Claim.item_type == C.CLAIM_ITEM_DONATION, Claim.item_id == item.id
        ).delete(synchronize_session=False)
        db.delete(item)
    db.query(Notification).filter(Notification.user_id == user.id).delete(synchronize_session=False)
    db.query(Message).filter(Message.sender_id == user.id).delete(synchronize_session=False)
    db.query(Report).filter(Report.reporter_id == user.id).delete(synchronize_session=False)
    db.query(Report).filter(
        Report.target_type == C.REPORT_TARGET_USER, Report.target_id == user.id
    ).delete(synchronize_session=False)
    db.delete(user)
    db.commit()


@pytest.fixture(scope="session", autouse=True)
def purge_test_users():
    """Remove everything the suite created in findback_test after the run."""
    yield
    db = SessionLocal()
    try:
        test_users = db.query(User).filter(User.email.like("%@pytest.local")).all()
        for test_user in test_users:
            _purge_user(db, test_user)
    finally:
        db.close()
