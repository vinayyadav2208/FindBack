"""Phase 15: rate limiter unit tests + security headers through the app."""

from __future__ import annotations

import time

from app.middleware import SlidingWindowRateLimiter


def test_allows_up_to_limit_then_blocks():
    limiter = SlidingWindowRateLimiter(60)
    for _ in range(5):
        allowed, _ = limiter.check("k", 5)
        assert allowed
    allowed, retry_after = limiter.check("k", 5)
    assert not allowed
    assert retry_after >= 1


def test_window_slides_and_frees_slots():
    limiter = SlidingWindowRateLimiter(0.05)
    for _ in range(3):
        assert limiter.check("k", 3)[0]
    assert not limiter.check("k", 3)[0]
    time.sleep(0.06)
    assert limiter.check("k", 3)[0]


def test_buckets_are_isolated():
    limiter = SlidingWindowRateLimiter(60)
    assert limiter.check("a", 1)[0]
    assert not limiter.check("a", 1)[0]
    assert limiter.check("b", 1)[0]  # different key unaffected


def test_zero_or_negative_limit_means_unlimited():
    limiter = SlidingWindowRateLimiter(60)
    for _ in range(10):
        assert limiter.check("k", 0)[0]


def test_reset_clears_everything():
    limiter = SlidingWindowRateLimiter(60)
    assert limiter.check("k", 1)[0]
    assert not limiter.check("k", 1)[0]
    limiter.reset()
    assert limiter.check("k", 1)[0]


def test_security_headers_present(client):
    response = client.get("/")
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "SAMEORIGIN"
    assert response.headers["Referrer-Policy"] == "no-referrer"


def test_headers_present_on_error_responses(client):
    response = client.get("/lost-items/999999999")
    assert response.status_code == 404
    assert response.headers["X-Content-Type-Options"] == "nosniff"


def test_rate_limit_header_absent_when_disabled(client):
    # RATE_LIMIT_ENABLED=false in the test environment
    response = client.get("/")
    assert "X-RateLimit-Limit" not in response.headers
