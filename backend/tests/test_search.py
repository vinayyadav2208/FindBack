"""Phase 7: global search, nearby, stats."""

from __future__ import annotations


def test_global_search_across_types(client, register):
    headers, _ = register()
    client.post(
        "/lost-items",
        json={"name": "Amber Perfume Bottle", "description": "lost amber perfume",
              "category": "Other", "location": "KPHB"},
        headers=headers,
    )

    result = client.get("/search", params={"q": "amber perfume"}).json()
    assert result["total"] >= 1
    assert any(i["type"] == "LOST" and i["name"] == "Amber Perfume Bottle" for i in result["items"])

    only_lost = client.get("/search", params={"q": "amber", "type": "LOST"}).json()
    assert all(i["type"] == "LOST" for i in only_lost["items"])

    assert client.get("/search", params={"q": ""}).status_code == 422


def test_nearby_returns_distance_sorted(client, register):
    headers, _ = register()
    client.post(
        "/lost-items",
        json={"name": "Nearby Marker Item", "description": "marker", "category": "Other",
              "location": "JNTU", "latitude": 17.4930, "longitude": 78.3920},
        headers=headers,
    )

    result = client.get(
        "/nearby", params={"lat": 17.4927, "lon": 78.3915, "radius_km": 5, "type": "LOST"}
    ).json()
    marker = [i for i in result["items"] if i["name"] == "Nearby Marker Item"]
    assert marker, result
    assert marker[0]["distance_km"] < 5
    distances = [i["distance_km"] for i in result["items"]]
    assert distances == sorted(distances)

    far_away = client.get(
        "/nearby", params={"lat": 12.9716, "lon": 77.5946, "radius_km": 0.5}
    ).json()
    assert not any(i["name"] == "Nearby Marker Item" for i in far_away["items"])


def test_stats_counts(client):
    stats = client.get("/stats")
    assert stats.status_code == 200
    body = stats.json()
    assert body["lost_items"] >= 4  # preserved development data
    for key in ("users", "found_items", "donations", "lost_active", "donations_available"):
        assert key in body
