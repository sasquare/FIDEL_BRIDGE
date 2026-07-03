"""Trust Score: a transparent 0-100 score derived entirely from real
signals - never a black box, never fabricated.

Weights live here, in one place, specifically so they can be retuned
later (e.g. once there's enough real user behaviour to justify it)
without touching the model or any template that displays the score.
"""

TRUST_SCORE_WEIGHTS = {
    # Proven track record (verified + rating + review volume + completed
    # jobs = 80 pts) outweighs profile completion (20 pts) - completion is
    # real but bounded, so it can't let form-filling outrank an actually
    # verified, well-reviewed professional.
    "verified": 35,
    "rating": 25,
    "review_volume": 10,
    "completed_jobs": 10,
    "profile_completion": 20,
}

# Review volume and completed-job counts are capped so one outlier
# (e.g. a professional with 500 jobs) can't dominate the score - being
# reliably good matters more than being prolific.
REVIEW_VOLUME_CAP = 10
COMPLETED_JOBS_CAP = 10


def compute_trust_score(professional):
    weights = TRUST_SCORE_WEIGHTS
    score = weights["verified"] if professional.is_verified else 0

    # smoothed_rating (Bayesian-blended with the platform average - see
    # app/utils/rating.py) rather than the raw average: a professional with
    # zero reviews previously scored 0 rating points here, identical to a
    # professional with a genuinely poor track record. smoothed_rating is
    # never None, so a brand-new professional now gets a neutral,
    # platform-average rating contribution instead of a penalty for simply
    # being new.
    score += (professional.smoothed_rating / 5) * weights["rating"]

    score += min(professional.review_count, REVIEW_VOLUME_CAP) / REVIEW_VOLUME_CAP * weights["review_volume"]
    score += (
        min(professional.completed_jobs_count, COMPLETED_JOBS_CAP) / COMPLETED_JOBS_CAP * weights["completed_jobs"]
    )
    score += (professional.profile_completion_percentage / 100) * weights["profile_completion"]

    return round(score)
