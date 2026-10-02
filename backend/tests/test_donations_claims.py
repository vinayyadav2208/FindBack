"""Phases 8-9: donations and claims."""

from __future__ import annotations


def _donation(client, headers, name="Test Wooden Chair"):
    response = client.post("/donations", json={
        "name": name,
        "description": "free to collect, wooden chair in good shape",
        "category": "Other",
        "condition": "GOOD",
        "location": "KPHB Hyderabad",
        "latitude": 17.4050,
        "longitude": 78.4820,
    }, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()["donation"]["id"]


def test_donation_crud_and_filters(client, register):
    owner, _ = register()
    donor, _ = register()
    donation_id = _donation(client, owner)

    assert client.get(f"/donations/{donation_id}").json()["status"] == "AVAILABLE"

    mine = client.get("/my-donations", headers=owner).json()
    assert any(i["id"] == donation_id for i in mine["items"])

    filtered = client.get("/donations", params={"q": "wooden chair", "condition": "GOOD"}).json()
    assert any(i["id"] == donation_id for i in filtered["items"])

    updated = client.put(f"/donations/{donation_id}", json={"name": "Chair Deluxe"}, headers=owner)
    assert updated.status_code == 200 and updated.json()["donation"]["name"] == "Chair Deluxe"

    # ownership
    assert client.put(f"/donations/{donation_id}", json={"name": "nope"}, headers=donor).status_code == 403
    assert client.delete(f"/donations/{donation_id}", headers=donor).status_code == 403
    assert client.delete(f"/donations/{donation_id}", headers=owner).status_code == 200
    assert client.get(f"/donations/{donation_id}").status_code == 404


def test_donation_claim_lifecycle(client, register):
    owner, _ = register()
    taker, _ = register()
    donation_id = _donation(client, owner, name="Test Bicycle Stand")

    # owner cannot claim own donation
    assert client.post(f"/donations/{donation_id}/claim", json={"message": "me"}, headers=owner).status_code == 400

    claim = client.post(
        f"/donations/{donation_id}/claim",
        json={"message": "I would like it"}, headers=taker,
    )
    assert claim.status_code == 201, claim.text
    assert claim.json()["status"] == "PENDING"
    claim_id = claim.json()["claim_id"]

    assert client.get(f"/donations/{donation_id}").json()["status"] == "RESERVED"

    # duplicate claim blocked
    other, _ = register()
    assert client.post(f"/donations/{donation_id}/claim", json={"message": "x"}, headers=other).status_code == 409

    # claimant cannot approve their own claim
    assert client.post(f"/claims/{claim_id}/approve", json={}, headers=taker).status_code == 403

    approved = client.post(f"/claims/{claim_id}/approve", json={"note": "ok"}, headers=owner)
    assert approved.status_code == 200 and approved.json()["claim"]["status"] == "APPROVED"
    assert client.get(f"/donations/{donation_id}").json()["status"] == "CLAIMED"

    # double approval conflicts
    assert client.post(f"/claims/{claim_id}/approve", json={}, headers=owner).status_code == 409

    # owner got notified
    notifications = client.get("/notifications", headers=owner).json()
    assert any("Bicycle Stand" in n["title"] for n in notifications["items"])


def test_found_item_claim_flow(client, register):
    owner, _ = register()
    claimant, _ = register()
    found = client.post("/found-items", json={
        "name": "Found Silver Watch", "description": "titan watch found",
        "category": "Other", "location": "JNTU",
    }, headers=owner)
    found_id = found.json()["item_id"]

    claim = client.post(
        "/claims",
        params={"item_type": "FOUND_ITEM", "item_id": found_id},
        json={"message": "it has my initials", "verification_answers": {"brand": "titan"}},
        headers=claimant,
    )
    assert claim.status_code == 201, claim.text
    claim_id = claim.json()["claim_id"]
    assert client.get(f"/found-items/{found_id}").json()["status"] == "CLAIMED"

    # verification answers are private
    detail = client.get(f"/claims/{claim_id}", headers=claimant)
    assert detail.status_code == 200 and detail.json()["verification_answers"]["brand"] == "titan"
    outsider, _ = register()
    assert client.get(f"/claims/{claim_id}", headers=outsider).status_code == 403

    # received / mine views
    assert any(c["id"] == claim_id for c in client.get("/claims/received", headers=owner).json()["items"])
    assert any(c["id"] == claim_id for c in client.get("/my-claims", headers=claimant).json()["items"])

    # reject restores ACTIVE
    rejected = client.post(f"/claims/{claim_id}/reject", json={"note": "wrong"}, headers=owner)
    assert rejected.status_code == 200 and rejected.json()["claim"]["status"] == "REJECTED"
    assert client.get(f"/found-items/{found_id}").json()["status"] == "ACTIVE"

    # second claim approves -> RETURNED
    claim2 = client.post(
        "/claims", params={"item_type": "FOUND_ITEM", "item_id": found_id},
        json={"message": "mine"}, headers=claimant,
    ).json()
    assert client.post(f"/claims/{claim2['claim_id']}/approve", json={}, headers=owner).status_code == 200
    assert client.get(f"/found-items/{found_id}").json()["status"] == "RETURNED"

    # claim on a resolved listing conflicts
    claim3 = client.post(
        "/claims", params={"item_type": "FOUND_ITEM", "item_id": found_id},
        json={"message": "late"}, headers=outsider,
    )
    assert claim3.status_code == 409


def test_lost_item_found_claim_and_cancel(client, register):
    owner, _ = register()
    finder, _ = register()
    lost = client.post("/lost-items", json={
        "name": "Lost Keys Ganesha", "description": "keys with ganesha keychain",
        "category": "Keys", "location": "KPHB",
    }, headers=owner)
    lost_id = lost.json()["item_id"]

    claim = client.post(
        "/claims", params={"item_type": "LOST_ITEM", "item_id": lost_id},
        json={"message": "found at metro gate"}, headers=finder,
    )
    assert claim.status_code == 201
    claim_id = claim.json()["claim_id"]
    assert client.get(f"/lost-items/{lost_id}").json()["status"] == "CLAIMED"

    cancelled = client.post(f"/claims/{claim_id}/cancel", headers=finder)
    assert cancelled.status_code == 200 and cancelled.json()["claim"]["status"] == "CANCELLED"
    assert client.get(f"/lost-items/{lost_id}").json()["status"] == "ACTIVE"

    # only the claimant can cancel
    claim2 = client.post(
        "/claims", params={"item_type": "LOST_ITEM", "item_id": lost_id},
        json={"message": "again"}, headers=finder,
    ).json()
    other, _ = register()
    assert client.post(f"/claims/{claim2['claim_id']}/cancel", headers=other).status_code == 403


def test_claim_validations(client, register):
    headers, _ = register()
    assert client.post(
        "/claims", params={"item_type": "BOGUS", "item_id": 1}, json={"message": "x"}, headers=headers
    ).status_code == 422
    assert client.post(
        "/claims", params={"item_type": "LOST_ITEM", "item_id": 999999999},
        json={"message": "x"}, headers=headers,
    ).status_code == 404
    assert client.post("/claims", params={"item_type": "LOST_ITEM", "item_id": 1}, json={"message": "x"}).status_code == 401
