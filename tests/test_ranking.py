from app.extensions import db
from app.models.booking import STATUS_COMPLETED, Booking
from app.models.customer import CustomerProfile
from app.models.professional import ProfessionalProfile
from app.models.review import Review
from app.models.user import User
from app.utils.rating import NEUTRAL_RATING_FALLBACK, bayesian_average, platform_average_rating
from app.utils.trust_score import TRUST_SCORE_WEIGHTS, compute_trust_score


def _make_professional(app, category_id, full_name="Chidi Okafor", email="chidi@example.com", verified=False):
    with app.app_context():
        user = User(full_name=full_name, email=email, role="professional")
        user.set_password("supersecret")
        user.professional_profile = ProfessionalProfile(
            profession="Plumber", category_id=category_id, city="Lagos", is_verified=verified
        )
        db.session.add(user)
        db.session.commit()
        return user.id


def _add_reviews(app, professional_user_id, ratings):
    with app.app_context():
        professional = db.session.get(User, professional_user_id).professional_profile

        customer_user = User(
            full_name="Ada Customer", email=f"customer-{professional_user_id}-{len(ratings)}@example.com", role="customer"
        )
        customer_user.set_password("supersecret")
        customer_user.customer_profile = CustomerProfile()
        db.session.add(customer_user)
        db.session.commit()
        customer_profile_id = customer_user.customer_profile.id

        for rating in ratings:
            booking = Booking(
                customer_profile_id=customer_profile_id,
                professional_profile_id=professional.id,
                title="Fix the wiring",
                description="Kitchen socket isn't working.",
                status=STATUS_COMPLETED,
            )
            db.session.add(booking)
            db.session.commit()
            db.session.add(
                Review(
                    booking_id=booking.id,
                    customer_profile_id=customer_profile_id,
                    professional_profile_id=professional.id,
                    rating=rating,
                )
            )
        db.session.commit()


# ---------------------------------------------------------------------------
# bayesian_average (pure function, no DB)
# ---------------------------------------------------------------------------


def test_bayesian_average_with_zero_reviews_returns_platform_average():
    assert bayesian_average(review_count=0, raw_average=0, platform_average=4.2) == 4.2


def test_bayesian_average_blends_prior_with_real_reviews():
    # confidence=5 phantom reviews at 4.0, blended with 5 real 5-star reviews:
    # (5*4.0 + 5*5.0) / (5+5) = 4.5
    result = bayesian_average(review_count=5, raw_average=5.0, platform_average=4.0)
    assert result == 4.5


def test_bayesian_average_converges_toward_raw_average_with_more_reviews():
    few_reviews = bayesian_average(review_count=2, raw_average=5.0, platform_average=3.0)
    many_reviews = bayesian_average(review_count=200, raw_average=5.0, platform_average=3.0)
    # Both are pulled below 5.0 by the prior, but many_reviews should be
    # pulled much less than few_reviews - the professional's own track
    # record should dominate once there's enough of it.
    assert few_reviews < many_reviews < 5.0


def test_bayesian_average_one_bad_review_does_not_sink_a_proven_professional():
    # A professional with 49 five-star reviews and one 1-star outlier
    # should still land far above someone with a single lucky 5-star review.
    proven = bayesian_average(review_count=50, raw_average=(49 * 5 + 1) / 50, platform_average=4.0)
    lucky_newcomer = bayesian_average(review_count=1, raw_average=5.0, platform_average=4.0)
    assert proven > lucky_newcomer


# ---------------------------------------------------------------------------
# platform_average_rating (DB-backed)
# ---------------------------------------------------------------------------


def test_platform_average_rating_falls_back_when_no_reviews_exist(app):
    with app.app_context():
        assert platform_average_rating() == NEUTRAL_RATING_FALLBACK


def test_platform_average_rating_reflects_real_reviews(app, category):
    user_id = _make_professional(app, category)
    _add_reviews(app, user_id, [5, 3])

    with app.app_context():
        assert platform_average_rating() == 4.0


# ---------------------------------------------------------------------------
# ProfessionalProfile.smoothed_rating
# ---------------------------------------------------------------------------


def test_smoothed_rating_is_never_none_for_a_professional_with_no_reviews(app, category):
    user_id = _make_professional(app, category)

    with app.app_context():
        professional = db.session.get(User, user_id).professional_profile
        assert professional.average_rating is None  # the raw property is still None
        assert professional.smoothed_rating == NEUTRAL_RATING_FALLBACK  # the scoring property is not


# ---------------------------------------------------------------------------
# compute_trust_score: the cold-start fix in practice
# ---------------------------------------------------------------------------


def test_trust_score_gives_new_verified_professional_nonzero_rating_credit(app, category):
    user_id = _make_professional(app, category, verified=True)

    with app.app_context():
        professional = db.session.get(User, user_id).professional_profile
        score = compute_trust_score(professional)
        # Before this fix, a 0-review professional got 0 rating points here.
        # Now they get platform-average-based credit immediately: verified
        # (35) alone would be 35, but the smoothed rating component should
        # push it meaningfully higher.
        assert score > TRUST_SCORE_WEIGHTS["verified"]


def test_trust_score_still_rewards_a_proven_high_rating_over_an_unproven_average_one(app, category):
    strong_id = _make_professional(app, category, full_name="Strong Pro", email="strong@example.com", verified=True)
    new_id = _make_professional(app, category, full_name="New Pro", email="new@example.com", verified=True)
    _add_reviews(app, strong_id, [5, 5, 5, 5, 5])

    with app.app_context():
        strong = db.session.get(User, strong_id).professional_profile
        new = db.session.get(User, new_id).professional_profile
        assert compute_trust_score(strong) > compute_trust_score(new)
