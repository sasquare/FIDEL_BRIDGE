from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.utils.badges import (
    FAST_RESPONDER_MAX_MINUTES,
    FAST_RESPONDER_MIN_RESPONSES,
    NEW_AND_PROMISING_MIN_COMPLETION,
    TOP_RATED_MIN_RATING,
    TOP_RATED_MIN_REVIEWS,
    compute_badges,
    is_fast_responder,
    is_highly_trusted,
    is_new_and_promising,
    is_recently_active,
    is_top_rated,
    is_verified,
)
from app.utils.best_match import COLD_START_BOOST_DAYS


def _professional(**overrides):
    defaults = dict(
        is_verified=False,
        verified_at=None,
        review_count=0,
        smoothed_rating=4.0,
        trust_score=50,
        response_count=0,
        average_response_minutes=None,
        last_active_at=None,
        profile_completion_percentage=0,
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def test_is_verified_mirrors_the_flag():
    assert is_verified(_professional(is_verified=True)) is True
    assert is_verified(_professional(is_verified=False)) is False


def test_top_rated_requires_both_rating_and_volume():
    high_rating_low_volume = _professional(smoothed_rating=5.0, review_count=1)
    assert is_top_rated(high_rating_low_volume) is False

    high_rating_high_volume = _professional(smoothed_rating=TOP_RATED_MIN_RATING, review_count=TOP_RATED_MIN_REVIEWS)
    assert is_top_rated(high_rating_high_volume) is True

    mediocre_rating_high_volume = _professional(smoothed_rating=4.0, review_count=50)
    assert is_top_rated(mediocre_rating_high_volume) is False


def test_highly_trusted_threshold():
    assert is_highly_trusted(_professional(trust_score=84)) is False
    assert is_highly_trusted(_professional(trust_score=85)) is True


def test_fast_responder_requires_both_speed_and_a_sample_size():
    one_lucky_fast_reply = _professional(response_count=1, average_response_minutes=5)
    assert is_fast_responder(one_lucky_fast_reply) is False

    consistently_fast = _professional(
        response_count=FAST_RESPONDER_MIN_RESPONSES, average_response_minutes=FAST_RESPONDER_MAX_MINUTES
    )
    assert is_fast_responder(consistently_fast) is True

    consistently_slow = _professional(response_count=10, average_response_minutes=500)
    assert is_fast_responder(consistently_slow) is False


def test_recently_active_requires_recent_data():
    now = datetime.now(timezone.utc)
    assert is_recently_active(_professional(last_active_at=None), now=now) is False
    assert is_recently_active(_professional(last_active_at=now - timedelta(days=1)), now=now) is True
    assert is_recently_active(_professional(last_active_at=now - timedelta(days=30)), now=now) is False


def test_new_and_promising_requires_verification_effort_and_no_track_record_yet():
    now = datetime.now(timezone.utc)

    unverified = _professional(is_verified=False, profile_completion_percentage=100)
    assert is_new_and_promising(unverified, now=now) is False

    verified_but_has_reviews = _professional(
        is_verified=True, verified_at=now - timedelta(days=1), review_count=3, profile_completion_percentage=100
    )
    assert is_new_and_promising(verified_but_has_reviews, now=now) is False

    verified_low_effort = _professional(
        is_verified=True,
        verified_at=now - timedelta(days=1),
        review_count=0,
        profile_completion_percentage=NEW_AND_PROMISING_MIN_COMPLETION - 1,
    )
    assert is_new_and_promising(verified_low_effort, now=now) is False

    verified_outside_window = _professional(
        is_verified=True,
        verified_at=now - timedelta(days=COLD_START_BOOST_DAYS + 1),
        review_count=0,
        profile_completion_percentage=100,
    )
    assert is_new_and_promising(verified_outside_window, now=now) is False

    genuinely_new_and_promising = _professional(
        is_verified=True,
        verified_at=now - timedelta(days=2),
        review_count=0,
        profile_completion_percentage=NEW_AND_PROMISING_MIN_COMPLETION,
    )
    assert is_new_and_promising(genuinely_new_and_promising, now=now) is True


def test_compute_badges_combines_and_orders_by_priority():
    now = datetime.now(timezone.utc)
    star_professional = _professional(
        is_verified=True,
        trust_score=90,
        smoothed_rating=5.0,
        review_count=20,
        response_count=10,
        average_response_minutes=20,
        last_active_at=now - timedelta(hours=1),
    )
    badges = compute_badges(star_professional, now=now)
    assert badges == ["verified", "highly_trusted", "top_rated", "fast_responder", "recently_active"]
    assert "best_match" not in badges  # never computed here - see the module docstring


def test_compute_badges_empty_for_a_professional_with_no_signals_yet():
    assert compute_badges(_professional()) == []
