"""Phases 11 + 14: uploads and admin dashboard."""

from __future__ import annotations

import io

PNG_BYTES = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108020000009077"
    "53de0000000c4944415408d763f8cfc000000301010018dd8db00000000049454e44ae426082"
)


def test_upload_validation(client, user):
    assert client.post("/uploads").status_code == 401

    ok = client.post(
        "/uploads", files={"file": ("t.png", io.BytesIO(PNG_BYTES), "image/png")}, headers=user
    )
    assert ok.status_code == 200 and ok.json()["url"].startswith("/media/")
    served = client.get(ok.json()["url"])
    assert served.status_code == 200 and "image" in served.headers["content-type"]

    exe = client.post(
        "/uploads", files={"file": ("e.exe", io.BytesIO(b"MZ\x90\x00"), "image/png")}, headers=user
    )
    assert exe.status_code == 415

    fake = client.post(
        "/uploads", files={"file": ("f.png", io.BytesIO(b"nonsense"), "image/png")}, headers=user
    )
    assert fake.status_code == 415

    big = client.post(
        "/uploads",
        files={"file": ("b.png", io.BytesIO(b"\x89PNG\r\n\x1a\n" + b"a" * (6 * 1024 * 1024)), "image/png")},
        headers=user,
    )
    assert big.status_code == 413


def test_admin_requires_admin_role(client, user, admin):
    for path in ("/admin/stats", "/admin/users", "/admin/reports", "/admin/claims"):
        assert client.get(path, headers=user).status_code == 403
        assert client.get(path, headers=admin).status_code == 200


def test_admin_stats_shape(client, admin):
    stats = client.get("/admin/stats", headers=admin).json()
    for section in ("users", "listings", "matches", "claims", "reports"):
        assert section in stats
    assert stats["users"]["total"] >= 2


def test_admin_user_moderation(client, admin, register):
    victim_headers, victim = register()

    listing = client.get("/admin/users", params={"q": victim["email"]}, headers=admin).json()
    assert listing["total"] == 1
    victim_id = listing["items"][0]["id"]

    assert client.put(f"/admin/users/{victim_id}/suspend", headers=admin).status_code == 200
    assert client.get("/me", headers=victim_headers).status_code == 403  # suspended

    assert client.put(f"/admin/users/{victim_id}/activate", headers=admin).status_code == 200
    assert client.get("/me", headers=victim_headers).status_code == 200

    promoted = client.put(
        f"/admin/users/{victim_id}/role", params={"role": "ADMIN"}, headers=admin
    )
    assert promoted.status_code == 200
    assert client.put(
        f"/admin/users/{victim_id}/role", params={"role": "BOGUS"}, headers=admin
    ).status_code == 422
    client.put(f"/admin/users/{victim_id}/role", params={"role": "USER"}, headers=admin)

    # admins cannot suspend or demote themselves
    admin_user = client.get("/me", headers=admin).json()
    assert client.put(
        f"/admin/users/{admin_user['id']}/suspend", headers=admin
    ).status_code == 400
    assert client.put(
        f"/admin/users/{admin_user['id']}/role", params={"role": "USER"}, headers=admin
    ).status_code == 400


def test_admin_listings_and_reports(client, admin, register):
    owner, _ = register()
    lost_id = client.post("/lost-items", json={
        "name": "Admin Moderated Item", "description": "will be removed",
        "category": "Other", "location": "KPHB",
    }, headers=owner).json()["item_id"]

    listings = client.get("/admin/listings", params={"q": "moderated"}, headers=admin).json()
    assert any(i["id"] == lost_id for i in listings["items"])

    # report queue
    reporter, _ = register()
    report = client.post("/reports", json={
        "target_type": "LOST_ITEM", "target_id": lost_id, "reason": "SCAM",
    }, headers=reporter).json()["report"]
    queue = client.get("/admin/reports", params={"status": "OPEN"}, headers=admin).json()
    assert any(r["id"] == report["id"] for r in queue["items"])

    reviewed = client.put(
        f"/admin/reports/{report['id']}", json={"status": "RESOLVED"}, headers=admin
    )
    assert reviewed.status_code == 200 and reviewed.json()["report"]["status"] == "RESOLVED"

    # moderation delete + notification to the owner
    assert client.delete(f"/admin/listings/LOST/{lost_id}", headers=admin).status_code == 200
    assert client.get(f"/lost-items/{lost_id}").status_code == 404
    notes = client.get("/notifications", headers=owner).json()
    assert any("removed" in n["title"].lower() for n in notes["items"])

    # non-admin cannot delete via admin route; admin can
    other = client.post("/lost-items", json={
        "name": "Still Here", "description": "x", "category": "Other", "location": "KPHB",
    }, headers=owner).json()["item_id"]
    assert client.delete(f"/admin/listings/LOST/{other}", headers=owner).status_code == 403
    assert client.delete(f"/admin/listings/LOST/{other}", headers=admin).status_code == 200
