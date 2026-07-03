"""Trust badges shown to customers - never a raw score, always a plain-
English reason to trust a professional. Every badge here is computed
from signals already feeding Trust Score (app/utils/trust_score.py) and
Best Match (app/utils/best_match.py) - never a separate, parallel
calculation - so a badge and a professional's rank can never quietly
disagree with each other.

"Best Match" is the one exception, deliberately not included here: it's
derived from a professional's rank within one specific search's results,
not from the professional alone, so it's computed at the route level
(see browse/routes.py) after the composite scores for that search are
already known.

"Popular in your area" (from the design doc) is deferred - it needs a
per-location peer comparison (a percentile within the customer's city or
state), which is both more expensive to compute and, at today's
professional counts, a near-meaningless signal (a single job can make
someone "popular" among two local peers). Revisit once there's enough
professionals-per-location for the comparison to mean something.
"""
from datetime import datetime, timezone

from app.utils.best_match import COLD_START_BOOST_DAYS, as_aware_utc

TOP_RATED_MIN_RATING = 4.8
TOP_RATED_MIN_REVIEWS = 5

HIGHLY_TRUSTED_MIN_SCORE = 85

FAST_RESPONDER_MAX_MINUTES = 60
FAST_RESPONDER_MIN_RESPONSES = 3

RECENTLY_ACTIVE_MAX_DAYS = 7

# A newcomer needs to have clearly put in the effort (profile completion)
# to earn this badge - it's meant to single out promising new
# professionals, not every professional who just signed up.
NEW_AND_PROMISING_MIN_COMPLETION = 80

# Display order also doubles as priority when a template only has room
# to show a few badges - earlier entries are more informative/harder to
# earn, so they're worth showing first.
BADGE_LABELS = {
    "best_match": "Best Match",
    "verified": "Verified",
    "highly_trusted": "Highly Trusted",
    "top_rated": "Top Rated",
    "fast_responder": "Fast Responder",
    "recently_active": "Recently Active",
    "new_and_promising": "New & Promising",
}


def is_verified(professional):
    return bool(professional.is_verified)


def is_top_rated(professional):
    if professional.review_count < TOP_RATED_MIN_REVIEWS:
        return False
    return professional.smoothed_rating >= TOP_RATED_MIN_RATING


def is_highly_trusted(professional):
    return professional.trust_score >= HIGHLY_TRUSTED_MIN_SCORE


def is_fast_responder(professional):
    if professional.response_count < FAST_RESPONDER_MIN_RESPONSES:
        return False
    minutes = professional.average_response_minutes
    return minutes is not None and minutes <= FAST_RESPONDER_MAX_MINUTES


def is_recently_active(professional, now=None):
    last_active = professional.last_active_at
    if last_active is None:
        return False
    now = now or datetime.now(timezone.utc)
    days = (now - as_aware_utc(last_active)).total_seconds() / 86400
    return days <= RECENTLY_ACTIVE_MAX_DAYS


def is_new_and_promising(professional, now=None):
    """An honest, positive way to present a good newcomer - verified,
    clearly put in the effort on their profile, no negative signals yet
    (zero reviews, not one bad one), and still within the same cold-start
    window that grants the temporary Best Match ranking boost."""
    if not professional.is_verified or professional.verified_at is None:
        return False
    if professional.review_count > 0:
        return False
    if professional.profile_completion_percentage < NEW_AND_PROMISING_MIN_COMPLETION:
        return False

    now = now or datetime.now(timezone.utc)
    days_since_verified = (now - as_aware_utc(professional.verified_at)).total_seconds() / 86400
    return days_since_verified <= COLD_START_BOOST_DAYS


def compute_badges(professional, now=None):
    """Every badge this professional currently earns, in BADGE_LABELS'
    display-priority order. "best_match" is never included here - see
    the module docstring."""
    checks = [
        ("verified", is_verified(professional)),
        ("highly_trusted", is_highly_trusted(professional)),
        ("top_rated", is_top_rated(professional)),
        ("fast_responder", is_fast_responder(professional)),
        ("recently_active", is_recently_active(professional, now=now)),
        ("new_and_promising", is_new_and_promising(professional, now=now)),
    ]
    return [key for key, earned in checks if earned]
