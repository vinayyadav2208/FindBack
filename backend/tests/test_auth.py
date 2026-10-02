"""Phase 2: authentication - registration, login, JWT, /me, guards."""

from __future__ import annotations

from jose import jwt


def test_register_returns_token_and_me_works(client):
    tag = "auth-ok"
    response = client.post("/auth/register", json={
        "name": "Alice", "email": f"{tag}@pytest.local", "password": "Str0ngPass!xyz",
    })
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["token_type"] == "bearer"
    headers = {"Authorization": f"Bearer {body['access_token']}"}
    me = client.get("/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["email"] == f"{tag}@pytest.local"
    assert me.json()["role"] == "USER"


def test_jwt_contains_expiration_claim(client):
    response = client.post("/auth/register", json={
        "name": "Bob", "email": "auth-exp@pytest.local", "password": "Str0ngPass!xyz",
    })
    claims = jwt.get_unverified_claims(response.json()["access_token"])
    assert "exp" in claims
    assert claims["exp"] > claims.get("iat", 0)


def test_duplicate_email_conflicts(client):
    payload = {"name": "Dup", "email": "auth-dup@pytest.local", "password": "Str0ngPass!xyz"}
    assert client.post("/auth/register", json=payload).status_code == 201
    assert client.post("/auth/register", json=payload).status_code == 409
    assert client.post("/users", json=payload).status_code == 409  # legacy JSON route too


def test_validation_rejections(client):
    weak = {"name": "W", "email": "auth-weak@pytest.local", "password": "abc"}
    assert client.post("/auth/register", json=weak).status_code == 422
    bad_email = {"name": "E", "email": "not-an-email", "password": "Str0ngPass!xyz"}
    assert client.post("/auth/register", json=bad_email).status_code == 422


def test_login_json_and_legacy_form(client):
    email, password = "auth-login@pytest.local", "Str0ngPass!xyz"
    client.post("/auth/register", json={"name": "L", "email": email, "password": password})

    ok = client.post("/auth/login", json={"email": email, "password": password})
    assert ok.status_code == 200 and ok.json()["access_token"]

    legacy = client.post("/login", data={"username": email, "password": password})
    assert legacy.status_code == 200 and legacy.json()["access_token"]

    wrong = client.post("/auth/login", json={"email": email, "password": "WrongPass1!"})
    assert wrong.status_code == 401
    unknown = client.post("/auth/login", json={"email": "ghost@pytest.local", "password": "x"})
    assert unknown.status_code == 401


def test_me_requires_valid_token(client):
    assert client.get("/me").status_code == 401
    assert client.get("/me", headers={"Authorization": "Bearer garbage"}).status_code == 401


def test_suspended_account_is_blocked(client, register):
    headers, user = register()
    from app import constants as C
    from app.database import SessionLocal
    from app.models import User

    db = SessionLocal()
    try:
        db.query(User).filter(User.id == user["id"]).update({"is_active": False})
        db.commit()
    finally:
        db.close()
    assert client.get("/me", headers=headers).status_code == 403
