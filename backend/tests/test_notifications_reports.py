"""Phases 12-13: notifications and reports."""

from __future__ import annotations


def test_notification_list_and_read_flows(client, register):
    owner, _ = register()
    taker, _ = register()

    donation = client.post("/donations", json={
        "name": "Old Monitor", "description": "free monitor", "category": "Other",
        "condition": "FAIR", "location": "KPHB",
    }, headers=owner).json()["donation"]["id"]
    client.post(f"/donations/{donation}/claim", json={"message": "want it"}, headers=taker)

    listing = client.get("/notifications", headers=owner).json()
    assert listing["unread"] >= 1
    assert any(n["type"] == "DONATION_CLAIMED" for n in listing["items"])

    unread_only = client.get("/notifications", params={"unread_only": True}, headers=owner).json()
    assert all(not n["is_read"] for n in unread_only["items"])

    count_before = client.get("/notifications/unread-count", headers=owner).json()["unread"]
    first_id = unread_only["items"][0]["id"]

    assert client.put(f"/notifications/{first_id}/read", headers=owner).status_code == 200
    assert client.get("/notifications/unread-count", headers=owner).json()["unread"] == count_before - 1

    # ownership: someone else's notification is a 404
    assert client.put(f"/notifications/{first_id}/read", headers=taker).status_code == 404
    assert client.put("/notifications/999999999/read", headers=owner).status_code == 404

    read_all = client.put("/notifications/read-all", headers=owner)
    assert read_all.status_code == 200
    assert client.get("/notifications/unread-count", headers=owner).json()["unread"] == 0

    assert client.get("/notifications").status_code == 401


def test_report_lifecycle(client, register):
    author, _ = register()
    reporter, _ = register()

    lost_id = client.post("/lost-items", json={
        "name": "Report Target Item", "description": "target", "category": "Other",
        "location": "KPHB",
    }, headers=author).json()["item_id"]

    report = client.post("/reports", json={
        "target_type": "LOST_ITEM", "target_id": lost_id,
        "reason": "SUSPICIOUS_BEHAVIOR", "description": "looks off",
    }, headers=reporter)
    assert report.status_code == 201, report.text
    report_id = report.json()["report"]["id"]

    # duplicate / missing target / invalid reason / self-report user
    assert client.post("/reports", json={
        "target_type": "LOST_ITEM", "target_id": lost_id, "reason": "SCAM",
    }, headers=reporter).status_code == 409
    assert client.post("/reports", json={
        "target_type": "LOST_ITEM", "target_id": 999999999, "reason": "SCAM",
    }, headers=reporter).status_code == 404
    assert client.post("/reports", json={
        "target_type": "LOST_ITEM", "target_id": lost_id, "reason": "NOT_A_REASON",
    }, headers=reporter).status_code == 422

    mine = client.get("/reports/mine", headers=reporter).json()
    assert any(r["id"] == report_id for r in mine["items"])

    other_view = client.get("/reports/mine", headers=author).json()
    assert not any(r["id"] == report_id for r in other_view["items"])

    assert client.post("/reports", json={
        "target_type": "USER", "target_id": 999999999, "reason": "SCAM",
    }, headers=reporter).status_code == 404
    assert client.get("/reports/mine").status_code == 401
