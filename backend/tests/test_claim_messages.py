"""Claim conversations: direct communication between the donor/listing owner
and the requester (the "acceptor"), plus notification deep-link fields."""

from __future__ import annotations


def _setup_donation_claim(client, register):
    """Donor lists a donation; a second user requests it."""
    donor_headers, donor = register()
    claimant_headers, claimant = register()

    created = client.post("/donations", json={
        "name": "Box of Academic Books",
        "description": "free box of engineering textbooks in good condition",
        "category": "Other",
        "condition": "GOOD",
        "location": "Gachibowli",
    }, headers=donor_headers)
    assert created.status_code == 201, created.text
    donation_id = created.json()["donation"]["id"]

    claim = client.post(
        f"/donations/{donation_id}/claim",
        json={"message": "I can pick the box up this evening."},
        headers=claimant_headers,
    )
    assert claim.status_code == 201, claim.text
    return donor_headers, donor, claimant_headers, claimant, donation_id, claim.json()["claim_id"]


def test_donor_and_acceptor_can_message(client, register):
    donor_headers, donor, claimant_headers, claimant, donation_id, claim_id = _setup_donation_claim(
        client, register
    )

    # the request itself produced a deep-linked DONATION_CLAIMED notice
    donor_notes = client.get("/notifications", headers=donor_headers).json()
    claimed_note = next(n for n in donor_notes["items"] if n["type"] == "DONATION_CLAIMED")
    assert claimed_note["related_type"] == "CLAIM"
    assert claimed_note["related_id"] == claim_id

    # the acceptor opens the conversation
    sent = client.post(
        f"/claims/{claim_id}/messages",
        json={"body": "Hi! Is the box still available? I can come by at 6pm."},
        headers=claimant_headers,
    )
    assert sent.status_code == 201, sent.text
    assert sent.json()["message_id"] > 0

    # the donor received a deep-linked MESSAGE_RECEIVED notification
    donor_notes = client.get("/notifications", headers=donor_headers).json()
    message_note = next(n for n in donor_notes["items"] if n["type"] == "MESSAGE_RECEIVED")
    assert message_note["related_type"] == "CLAIM"
    assert message_note["related_id"] == claim_id
    assert "come by at 6pm" in message_note["message"]
    assert "Box of Academic Books" in message_note["message"]
    assert "New message from" in message_note["title"]

    # the sender never notifies themselves
    claimant_notes = client.get("/notifications", headers=claimant_headers).json()
    assert not any(n["type"] == "MESSAGE_RECEIVED" for n in claimant_notes["items"])

    # unread badge: donor has 1, acceptor has 0 (global counter includes claims)
    assert client.get("/messages/unread-count", headers=donor_headers).json()["unread"] == 1
    assert client.get("/messages/unread-count", headers=claimant_headers).json()["unread"] == 0

    # per-claim unread badge on both list endpoints
    received = client.get("/claims/received", headers=donor_headers).json()
    row = next(c for c in received["items"] if c["id"] == claim_id)
    assert row["unread_messages"] == 1
    mine = client.get("/my-claims", headers=claimant_headers).json()
    row = next(c for c in mine["items"] if c["id"] == claim_id)
    assert row["unread_messages"] == 0

    # thread shows the sender name and stays claim-scoped
    thread = client.get(f"/claims/{claim_id}/messages", headers=donor_headers).json()
    assert thread["total"] == 1
    assert thread["items"][0]["sender_name"] == claimant["name"]
    assert thread["items"][0]["match_id"] is None
    assert thread["items"][0]["claim_id"] == claim_id


def test_claim_thread_read_flow_and_reply(client, register):
    donor_headers, donor, claimant_headers, claimant, donation_id, claim_id = _setup_donation_claim(
        client, register
    )

    client.post(
        f"/claims/{claim_id}/messages",
        json={"body": "Pickup at the main gate?"},
        headers=claimant_headers,
    )

    # donor opens the thread and marks it read
    thread = client.get(f"/claims/{claim_id}/messages", headers=donor_headers)
    assert thread.status_code == 200
    assert thread.json()["items"][0]["is_read"] is False

    read = client.post(f"/claims/{claim_id}/messages/read", headers=donor_headers)
    assert read.status_code == 200
    assert read.json()["updated"] == 1
    assert client.get("/messages/unread-count", headers=donor_headers).json()["unread"] == 0
    assert client.get(f"/claims/{claim_id}/messages", headers=donor_headers).json()["items"][0]["is_read"] is True

    # donor replies -> unread returns to the acceptor
    reply = client.post(
        f"/claims/{claim_id}/messages",
        json={"body": "Yes, gate 2 works for me."},
        headers=donor_headers,
    )
    assert reply.status_code == 201, reply.text
    assert client.get("/messages/unread-count", headers=claimant_headers).json()["unread"] == 1

    # marking read is idempotent
    again = client.post(f"/claims/{claim_id}/messages/read", headers=claimant_headers)
    assert again.json()["updated"] == 1
    assert client.get("/messages/unread-count", headers=claimant_headers).json()["unread"] == 0


def test_claim_thread_privacy(client, register, admin):
    donor_headers, _, claimant_headers, _, donation_id, claim_id = _setup_donation_claim(
        client, register
    )
    outsider, _ = register()

    # only the two parties (or an admin) may touch the thread
    assert client.get(f"/claims/{claim_id}/messages", headers=outsider).status_code == 403
    assert client.post(
        f"/claims/{claim_id}/messages", json={"body": "let me in"}, headers=outsider
    ).status_code == 403
    assert client.post(f"/claims/{claim_id}/messages/read", headers=outsider).status_code == 403

    # authentication is required everywhere
    assert client.get(f"/claims/{claim_id}/messages").status_code == 401
    assert client.post(f"/claims/{claim_id}/messages", json={"body": "hi"}).status_code == 401

    # missing claim -> 404, no information leak
    assert client.get("/claims/999999/messages", headers=donor_headers).status_code == 404

    # admins moderate (read) any claim thread
    assert client.get(f"/claims/{claim_id}/messages", headers=admin).status_code == 200

    # empty / whitespace-only bodies are rejected
    assert client.post(
        f"/claims/{claim_id}/messages", json={"body": "   "}, headers=donor_headers
    ).status_code == 422


def test_approval_notification_is_deep_linked(client, register):
    donor_headers, donor, claimant_headers, claimant, donation_id, claim_id = _setup_donation_claim(
        client, register
    )

    approved = client.post(f"/claims/{claim_id}/approve", json={"note": "Box is yours"}, headers=donor_headers)
    assert approved.status_code == 200, approved.text

    notes = client.get("/notifications", headers=claimant_headers).json()
    approval = next(n for n in notes["items"] if n["type"] == "CLAIM_APPROVED")
    assert approval["related_type"] == "CLAIM"
    assert approval["related_id"] == claim_id

    # conversation still works after approval - that is the handover channel
    sent = client.post(
        f"/claims/{claim_id}/messages",
        json={"body": "Great, collecting it tomorrow at noon."},
        headers=claimant_headers,
    )
    assert sent.status_code == 201, sent.text


def test_match_notifications_are_deep_linked(client, register):
    """MATCH_FOUND and match MESSAGE_RECEIVED carry related MATCH + id."""
    lost_headers, _ = register()
    found_headers, _ = register()

    lost = client.post("/lost-items", json={
        "name": "Graphite Tennis Racket",
        "description": "lost a graphite tennis racket with a red grip near the courts",
        "category": "Other",
        "location": "City Courts",
    }, headers=lost_headers)
    found = client.post("/found-items", json={
        "name": "Graphite Tennis Racket Found",
        "description": "found a graphite tennis racket with red grip at the city courts",
        "category": "Other",
        "location": "City Courts",
    }, headers=found_headers)
    assert lost.status_code == 201 and found.status_code == 201

    matches = client.get("/matches", headers=lost_headers).json()
    match = next(
        m for m in matches["items"]
        if m["lost_item_id"] == lost.json()["item_id"]
        and m["found_item_id"] == found.json()["item_id"]
    )

    # MATCH_FOUND notification points at the match
    notes = client.get("/notifications", headers=found_headers).json()
    match_note = next(n for n in notes["items"] if n["type"] == "MATCH_FOUND")
    assert match_note["related_type"] == "MATCH"
    assert match_note["related_id"] == match["id"]

    # ...and so does MESSAGE_RECEIVED once a conversation starts
    client.post(
        f"/matches/{match['id']}/messages",
        json={"body": "Is the red grip still on it?"},
        headers=lost_headers,
    )
    notes = client.get("/notifications", headers=found_headers).json()
    message_note = next(n for n in notes["items"] if n["type"] == "MESSAGE_RECEIVED")
    assert message_note["related_type"] == "MATCH"
    assert message_note["related_id"] == match["id"]
