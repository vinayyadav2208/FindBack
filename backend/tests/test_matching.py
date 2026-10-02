"""Phase 10: AI matching engine."""

from __future__ import annotations


def _create_pair(client, register):
    lost_headers, _ = register()
    found_headers, _ = register()

    lost = client.post("/lost-items", json={
        "name": "Neon Green Racing Bicycle",
        "description": "lost my neon green racing bicycle with bell near central plaza",
        "category": "Other",
        "location": "Central Plaza",
        "latitude": 17.4400,
        "longitude": 78.4500,
    }, headers=lost_headers)
    assert lost.status_code == 201, lost.text

    found = client.post("/found-items", json={
        "name": "Neon Green Bicycle Found",
        "description": "found a neon green racing bicycle with bell at central plaza",
        "category": "Other",
        "location": "Central Plaza",
        "latitude": 17.4410,
        "longitude": 78.4510,
    }, headers=found_headers)
    assert found.status_code == 201, found.text

    return lost_headers, found_headers, lost.json()["item_id"], found.json()["item_id"]


def test_matching_creates_explained_match(client, register):
    lost_headers, found_headers, lost_id, found_id = _create_pair(client, register)

    # BackgroundTasks run synchronously inside the TestClient request cycle.
    matches = client.get("/matches", headers=lost_headers).json()
    match = next(
        (m for m in matches["items"] if m["lost_item_id"] == lost_id and m["found_item_id"] == found_id),
        None,
    )
    assert match is not None, matches

    assert match["combined_score"] > 0
    assert match["text_score"] > 0.2
    assert match["category_score"] == 1.0
    assert match["location_score"] > 0.5
    assert match["lost_item"] and match["found_item"]

    explanation = match["explanation"]
    assert explanation["reasons"]
    assert "potential" in explanation["confidence"].lower() or "possible" in explanation["confidence"].lower()
    assert "verify ownership" in explanation["confidence_note"].lower()

    # both parties see it; outsiders do not
    assert any(
        m["lost_item_id"] == lost_id for m in client.get("/matches", headers=found_headers).json()["items"]
    )
    outsider, _ = register()
    assert client.get(f"/matches/{match['id']}", headers=outsider).status_code == 403

    # MATCH_FOUND notifications for both owners
    for headers in (lost_headers, found_headers):
        notes = client.get("/notifications", headers=headers).json()
        assert any(n["type"] == "MATCH_FOUND" for n in notes["items"])

    # opening marks VIEWED; status update works; invalid status rejected
    assert client.get(f"/matches/{match['id']}", headers=lost_headers).json()["status"] == "VIEWED"
    updated = client.put(
        f"/matches/{match['id']}/status", json={"status": "VERIFIED"}, headers=lost_headers
    )
    assert updated.status_code == 200 and updated.json()["match"]["status"] == "VERIFIED"
    assert client.put(
        f"/matches/{match['id']}/status", json={"status": "NOPE"}, headers=lost_headers
    ).status_code == 422

    # listings flipped to MATCHED (and remain claimable)
    assert client.get(f"/lost-items/{lost_id}").json()["status"] == "MATCHED"
    assert client.get(f"/found-items/{found_id}").json()["status"] == "MATCHED"


def test_no_false_positive_for_unrelated_items(client, register):
    headers, _ = register()
    lost = client.post("/lost-items", json={
        "name": "Titanium Aquarium Gravel",
        "description": "bag of aquarium gravel spilled, lost at pet store",
        "category": "Other", "location": "Gachibowli",
    }, headers=headers)
    lost_id = lost.json()["item_id"]

    matches = client.get("/matches", headers=headers).json()
    assert not any(m["lost_item_id"] == lost_id for m in matches["items"])


def test_rebuild_endpoint(client, register):
    headers, _ = register()
    response = client.post("/matches/rebuild", headers=headers)
    assert response.status_code == 200
    assert "new_matches" in response.json()
    assert client.post("/matches/rebuild").status_code == 401


def test_embedding_backend_never_fails():
    from app.services.embedding_service import cosine, embed_text, fallback_embedding

    a = embed_text("black leather wallet jntu metro")
    b = embed_text("wallet black leather found at jntu metro")
    c = embed_text("completely different topic about cooking pasta recipes")

    assert len(a) == len(b) == 384
    assert cosine(a, b) > cosine(a, c)
    assert fallback_embedding("")  # empty text returns a zero vector, not an error
