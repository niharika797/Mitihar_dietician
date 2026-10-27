"""Pure-logic checks for the friendly 429 helpers and the per-email limit (in-memory storage)."""
import json

import pytest
from dotenv import load_dotenv

load_dotenv()

from app.core import limiter as lim  # noqa: E402


@pytest.fixture()
def memory_limiter(monkeypatch):
    """Swap the module limiter for a fresh in-memory one so counts never leak between tests."""
    fresh = lim.FailOpenLimiter(key_func=lambda request: "test")
    monkeypatch.setattr(lim, "limiter", fresh)
    return fresh


@pytest.mark.parametrize("seconds, expected", [
    (1, "about 1 minute"),
    (59, "about 1 minute"),
    (61, "about 2 minutes"),
    (900, "about 15 minutes"),
    (3540, "about 59 minutes"),
    (3600, "about 1 hour"),
    (3601, "about 2 hours"),
])
def test_friendly_wait_rounds_up(seconds, expected):
    assert lim.friendly_wait(seconds) == expected


def test_message_is_professional_and_has_the_wait():
    msg = lim.rate_limit_message(720)
    assert "Too many attempts" in msg
    assert "take a break" in msg
    assert "try again in about 12 minutes" in msg


def test_response_has_status_header_and_seconds():
    r = lim.rate_limited_response(90)
    assert r.status_code == 429
    assert r.headers["retry-after"] == "90"
    body = json.loads(r.body)
    assert body["retry_after_seconds"] == 90
    assert "about 2 minutes" in body["detail"]


def test_response_never_says_zero_seconds():
    assert json.loads(lim.rate_limited_response(0).body)["retry_after_seconds"] == 1


def test_key_limit_allows_then_refuses(memory_limiter):
    for _ in range(3):
        lim.hit_key_limit("login", "a@example.com", "3/minute")
    with pytest.raises(lim.RateLimitedError) as exc:
        lim.hit_key_limit("login", "a@example.com", "3/minute")
    assert 1 <= exc.value.retry_after <= 60


def test_key_limit_ignores_case_and_spaces(memory_limiter):
    for _ in range(3):
        lim.hit_key_limit("login", "a@example.com", "3/minute")
    with pytest.raises(lim.RateLimitedError):
        lim.hit_key_limit("login", "  A@Example.com ", "3/minute")


def test_key_limit_is_per_email_and_per_scope(memory_limiter):
    for _ in range(3):
        lim.hit_key_limit("login", "a@example.com", "3/minute")
    lim.hit_key_limit("login", "b@example.com", "3/minute")        # other email: fine
    lim.hit_key_limit("register", "a@example.com", "3/minute")     # other scope: fine
