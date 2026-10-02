"""Match messaging: direct communication between the person who lost an item
and the person who found it, once the AI has paired their listings."""

from __future__ import annotations


def _create_match(client, register):
    """Register a lost-owner and a found-owner and pair their listings."""
    lost_headers, lost_user = register()
    found_headers, found_user = register()

    lost = client.post("/lost-items", json={
        "name": "Cobalt Blue Skate Helmet",
        "description": "lost a cobalt blue skate helmet with scratch on the side at riverside park",
        "category": "Other",
        "location": "Riverside Park",
    }, headers=lost_headers)
    assert lost.status_code == 201, lost.text

    found = client.post("/found-items", json={
        "name": "Cobalt Blue Helmet Found",
        "description": "found a cobalt blue skate helmet with a scratch at riverside park",
        "category": "Other",
        "location": "Riverside Park",
    }, headers=found_headers)
    assert found.status_code == 201, found.text

    lost_id, found_id = lost.json()["item_id"], found.json()["item_id"]
    matches = client.get("/matches", headers=lost_headers).json()
    match = next(
        (
            m for m in matches["items"]
            if m["lost_item_id"] == lost_id and m["found_item_id"] == found_id
        ),
        None,
    )
    assert match is not None, matches
    return lost_headers, lost_user, found_headers, found_user, match["id"]


def test_send_message_notifies_other_party_and_marks_contacted(client, register):
    lost_headers, lost_user, found_headers, found_user, match_id = _create_match(client, register)

    sent = client.post(
        f"/matches/{match_id}/messages",
        json={"body": "Hi! Is the scratch on the left side of the helmet?"},
        headers=lost_headers,
    )
    assert sent.status_code == 201, sent.text
    payload = sent.json()
    assert payload["message_id"] > 0
    # first contact advances the match
    assert payload["match"]["status"] == "CONTACTED"

    # the finder received a MESSAGE_RECEIVED notification with a snippet
    notes = client.get("/notifications", headers=found_headers).json()
    received = [n for n in notes["items"] if n["type"] == "MESSAGE_RECEIVED"]
    assert received, notes
    assert "scratch on the left side" in received[0]["message"]
    assert "New message from" in received[0]["title"]

    # the sender must never notify themselves
    sender_notes = client.get("/notifications", headers=lost_headers).json()
    assert not any(n["type"] == "MESSAGE_RECEIVED" for n in sender_notes["items"])

    # unread counts: finder has 1, sender has 0
    assert client.get("/messages/unread-count", headers=found_headers).json()["unread"] == 1
    assert client.get("/messages/unread-count", headers=lost_headers).json()["unread"] == 0

    # the match list exposes the per-thread unread badge
    found_matches = client.get("/matches", headers=found_headers).json()
    thread = next(m for m in found_matches["items"] if m["id"] == match_id)
    assert thread["unread_messages"] == 1
    lost_matches = client.get("/matches", headers=lost_headers).json()
    own = next(m for m in lost_matches["items"] if m["id"] == match_id)
    assert own["unread_messages"] == 0


def test_thread_read_flow_and_reply(client, register):
    lost_headers, lost_user, found_headers, found_user, match_id = _create_match(client, register)

    client.post(
        f"/matches/{match_id}/messages",
        json={"body": "I lost it around 6pm by the fountain."},
        headers=lost_headers,
    )

    # finder opens the thread: messages visible with sender name, then marked read
    thread = client.get(f"/matches/{match_id}/messages", headers=found_headers)
    assert thread.status_code == 200
    body = thread.json()
    assert body["total"] == 1
    first = body["items"][0]
    assert first["body"] == "I lost it around 6pm by the fountain."
    assert first["sender_name"] == lost_user["name"]
    assert first["is_read"] is False

    read = client.post(f"/matches/{match_id}/messages/read", headers=found_headers)
    assert read.status_code == 200
    assert read.json()["updated"] == 1
    assert client.get("/messages/unread-count", headers=found_headers).json()["unread"] == 0
    assert client.get(f"/matches/{match_id}/messages", headers=found_headers).json()["items"][0]["is_read"] is True

    # reply flips unread back to the original sender
    reply = client.post(
        f"/matches/{match_id}/messages",
        json={"body": "Found it! Meet at the park office?"},
        headers=found_headers,
    )
    assert reply.status_code == 201, reply.text
    assert client.get("/messages/unread-count", headers=lost_headers).json()["unread"] == 1

    # marking read is idempotent
    again = client.post(f"/matches/{match_id}/messages/read", headers=lost_headers)
    assert again.json()["updated"] == 1
    assert client.get("/messages/unread-count", headers=lost_headers).json()["unread"] == 0


def test_message_privacy(client, register, admin):
    lost_headers, _, found_headers, _, match_id = _create_match(client, register)
    outsider, _ = register()

    # only the two parties (or an admin) may read or write the thread
    assert client.get(f"/matches/{match_id}/messages", headers=outsider).status_code == 403
    assert client.post(
        f"/matches/{match_id}/messages", json={"body": "let me in"}, headers=outsider
    ).status_code == 403
    assert client.post(f"/matches/{match_id}/messages/read", headers=outsider).status_code == 403

    # authentication is required everywhere
    assert client.get(f"/matches/{match_id}/messages").status_code == 401
    assert client.post(f"/matches/{match_id}/messages", json={"body": "hi"}).status_code == 401
    assert client.get("/messages/unread-count").status_code == 401

    # an outsider has no match threads, so no unread messages
    assert client.get("/messages/unread-count", headers=outsider).json()["unread"] == 0

    # admins moderate (read) any thread
    assert client.get(f"/matches/{match_id}/messages", headers=admin).status_code == 200


def test_message_validation(client, register):
    headers, _ = register()
    lost = client.post("/lost-items", json={
        "name": "Silver Laptop Sleeve",
        "description": "lost a silver laptop sleeve with a red zip near the bus stop",
        "category": "Other", "location": "Mindspace",
    }, headers=headers)
    found = client.post("/found-items", json={
        "name": "Silver Laptop Sleeve Found",
        "description": "found a silver laptop sleeve with red zip at the bus stop mindspace",
        "category": "Other", "location": "Mindspace",
    }, headers=headers)
    matches = client.get("/matches", headers=headers).json()
    match = next(
        m for m in matches["items"]
        if m["lost_item_id"] == lost.json()["item_id"]
        and m["found_item_id"] == found.json()["item_id"]
    )

    # empty / whitespace-only bodies are rejected
    assert client.post(
        f"/matches/{match['id']}/messages", json={"body": ""}, headers=headers
    ).status_code == 422
    assert client.post(
        f"/matches/{match['id']}/messages", json={"body": "   "}, headers=headers
    ).status_code == 422

    # missing match -> 404 (for a party), not a leak
    assert client.post(
        "/matches/999999/messages", json={"body": "hello"}, headers=headers
    ).status_code == 404


def test_same_owner_match_never_self_notifies(client, register):
    """One user holding both sides of a match can chat without notifying self."""
    headers, me = register()
    lost = client.post("/lost-items", json={
        "name": "Amber Reading Glasses",
        "description": "lost amber reading glasses in a brown case near the cafe",
        "category": "Other", "location": "Campus Cafe",
    }, headers=headers)
    found = client.post("/found-items", json={
        "name": "Amber Reading Glasses Found",
        "description": "found amber reading glasses in a brown case at campus cafe",
        "category": "Other", "location": "Campus Cafe",
    }, headers=headers)
    matches = client.get("/matches", headers=headers).json()
    match = next(
        m for m in matches["items"]
        if m["lost_item_id"] == lost.json()["item_id"]
        and m["found_item_id"] == found.json()["item_id"]
    )

    sent = client.post(
        f"/matches/{match['id']}/messages", json={"body": "note to self: check the case"}
    , headers=headers)
    assert sent.status_code == 201, sent.text

    notes = client.get("/notifications", headers=headers).json()
    assert not any(n["type"] == "MESSAGE_RECEIVED" for n in notes["items"])
    # ...but the thread itself works
    thread = client.get(f"/matches/{match['id']}/messages", headers=headers).json()
    assert thread["total"] == 1
    assert thread["items"][0]["sender_id"] == me["id"]
