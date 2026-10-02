"""Phases 3-4: lost and found item CRUD, filters, ownership."""

from __future__ import annotations


def _lost_payload(**overrides):
    payload = {
        "name": "Test Nokia Phone",
        "description": "Lost a nokia phone near the bus stop",
        "category": "Phone",
        "location": "JNTU Hyderabad",
        "latitude": 17.4927,
        "longitude": 78.3915,
    }
    payload.update(overrides)
    return payload


def test_create_requires_auth(client):
    assert client.post("/lost-items", json=_lost_payload()).status_code == 401


def test_owner_comes_from_jwt_not_payload(client, register):
    headers, user = register()
    payload = _lost_payload()
    payload["user_id"] = 999999  # must be ignored
    response = client.post("/lost-items", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    item = response.json()  # create returns a flat object with item_id
    assert item["user_id"] == user["id"]
    assert item["category"] == "Phone"


def test_invalid_category_and_status_rejected(client, user):
    assert client.post("/lost-items", json=_lost_payload(category="Rocket"), headers=user).status_code == 422
    created = client.post("/lost-items", json=_lost_payload(), headers=user).json()
    bad = client.put(f"/lost-items/{created['item_id']}", json={"status": "INVENTED"}, headers=user)
    assert bad.status_code == 422


def test_crud_roundtrip_and_404(client, user):
    created = client.post("/lost-items", json=_lost_payload(), headers=user).json()
    item_id = created["item_id"]

    detail = client.get(f"/lost-items/{item_id}")
    assert detail.status_code == 200 and detail.json()["name"] == "Test Nokia Phone"
    assert client.get("/lost-items/999999999").status_code == 404

    updated = client.put(f"/lost-items/{item_id}", json={"description": "updated desc"}, headers=user)
    assert updated.status_code == 200 and updated.json()["item"]["description"] == "updated desc"

    assert client.delete(f"/lost-items/{item_id}", headers=user).status_code == 200
    assert client.get(f"/lost-items/{item_id}").status_code == 404


def test_ownership_enforced(client, register):
    headers_a, _ = register()
    headers_b, _ = register()
    item_id = client.post("/lost-items", json=_lost_payload(), headers=headers_a).json()["item_id"]

    assert client.put(f"/lost-items/{item_id}", json={"name": "hijack"}, headers=headers_b).status_code == 403
    assert client.delete(f"/lost-items/{item_id}", headers=headers_b).status_code == 403


def test_search_filters_and_pagination(client, user):
    client.post("/lost-items", json=_lost_payload(name="Purple Suitcase", category="Bag"), headers=user)
    client.post("/lost-items", json=_lost_payload(name="Brown Leather Bag", category="Bag"), headers=user)

    found = client.get("/lost-items", params={"q": "purple suitcase"}).json()
    assert any(i["name"] == "Purple Suitcase" for i in found["items"])

    filtered = client.get("/lost-items", params={"category": "Bag", "location": "JNTU"}).json()
    assert filtered["total"] >= 2

    page = client.get("/lost-items", params={"page": 1, "limit": 1}).json()
    assert len(page["items"]) == 1 and page["limit"] == 1 and page["pages"] >= 2

    nearby = client.get("/lost-items", params={"lat": 17.4927, "lon": 78.3915, "radius_km": 5}).json()
    assert any(i["name"] == "Purple Suitcase" for i in nearby["items"])


def test_my_lost_items_isolation(client, register):
    headers_a, _ = register()
    headers_b, _ = register()
    client.post("/lost-items", json=_lost_payload(name="Keys A"), headers=headers_a)
    client.post("/lost-items", json=_lost_payload(name="Keys B"), headers=headers_b)

    mine_a = client.get("/my-lost-items", headers=headers_a).json()
    mine_b = client.get("/my-lost-items", headers=headers_b).json()
    names_a = [i["name"] for i in mine_a["items"]]
    assert "Keys A" in names_a and "Keys B" not in names_a
    assert mine_a["total"] != mine_b["total"] or names_a != [i["name"] for i in mine_b["items"]]


def test_found_item_crud_and_my_found_items(client, register):
    headers, user = register()
    payload = {
        "name": "Found Blue Cap",
        "description": "blue cap found at metro",
        "category": "Other",
        "location": "JNTU Metro",
    }
    created = client.post("/found-items", json=payload, headers=headers)
    assert created.status_code == 201, created.text
    item_id = created.json()["item_id"]

    detail = client.get(f"/found-items/{item_id}")
    assert detail.status_code == 200 and detail.json()["user_id"] == user["id"]

    status_update = client.put(f"/found-items/{item_id}", json={"status": "RETURNED"}, headers=headers)
    assert status_update.status_code == 200

    mine = client.get("/my-found-items", headers=headers).json()
    assert any(i["id"] == item_id for i in mine["items"])

    assert client.delete(f"/found-items/{item_id}", headers=headers).status_code == 200
