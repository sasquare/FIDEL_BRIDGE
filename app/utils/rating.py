"""Bayesian-smoothed ratings.

A professional with one lucky 5-star review should not outrank one with a
proven 4.8-star average across fifty reviews, and a professional with zero
reviews should be scored as "unproven," never as if they were bad. Both
problems have the same fix: blend each professional's raw average with a
platform-wide prior, weighted by how many real reviews they actually have.

See the Best Match design doc, Section 3 ("Rating must never be used raw")
and Section 4 (Cold-Start Strategy).
"""
from sqlalchemy import func

from app.extensions import db
from app.models.review import Review

# "Phantom" reviews assumed at the platform average, blended with a
# professional's real reviews. Higher = new professionals take longer to
# pull away from the platform average; lower = individual reviews swing
# a new professional's score faster. 5 is a starting point, not a
# researched constant - tune once real review volume exists.
BAYESIAN_CONFIDENCE = 5

# Fallback prior for when the platform itself has no reviews yet at all
# (a brand-new deployment, or a test database). Deliberately above the
# 3.0 scale midpoint since real reviews leaving completed jobs on a
# service marketplace skew positive - most jobs that get reviewed at all
# went fine. This is a placeholder assumption, not derived from FidelBridge
# data yet, and should be revisited once there's enough real review volume
# to compute a genuine platform average with confidence.
NEUTRAL_RATING_FALLBACK = 4.0


def platform_average_rating():
    """The platform-wide average rating across every review, or the
    neutral fallback if there are no reviews anywhere yet."""
    avg = db.session.query(func.avg(Review.rating)).scalar()
    return float(avg) if avg is not None else NEUTRAL_RATING_FALLBACK


def bayesian_average(review_count, raw_average, platform_average=None):
    """Blend a professional's raw average rating with the platform-wide
    average, weighted by BAYESIAN_CONFIDENCE "phantom" reviews.

    review_count == 0 returns platform_average exactly (no reviews means
    no real signal to blend in). As review_count grows, the professional's
    own raw_average increasingly dominates the result.
    """
    if platform_average is None:
        platform_average = platform_average_rating()

    if not review_count:
        return platform_average

    return (BAYESIAN_CONFIDENCE * platform_average + review_count * raw_average) / (
        BAYESIAN_CONFIDENCE + review_count
    )
