from app.extensions import db
from app.models.booking import STATUS_COMPLETED, Booking
from app.models.customer import CustomerProfile
from app.models.professional import ProfessionalProfile
from app.models.review import Review
from app.models.user import User
from app.utils.best_match import (
    RELEVANCE_BIO_MATCH,
    RELEVANCE_CATEGORY_MATCH,
    RELEVANCE_EXACT_NAME,
    RELEVANCE_EXACT_PROFESSION,
    RELEVANCE_NAME_MATCH,
    RELEVANCE_NO_MATCH,
    RELEVANCE_PROFESSION_MATCH,
    RELEVANCE_SKILL_MATCH,
    text_relevance_score,
)
from app.utils.rating import NEUTRAL_RATING_FALLBACK, bayesian_average, platform_average_rating
from app.utils.trust_score import TRUST_SCORE_WEIGHTS, compute_trust_score


class _FakeUser:
    def __init__(self, full_name):
        self.full_name = full_name


class _FakeSkill:
    def __init__(self, name):
        self.name = name


class _FakeProfessional:
    """A lightweight stand-in for ProfessionalProfile - text_relevance_score
    only touches user.full_name, profession, bio, category_id and skills,
    so a real DB-backed professional isn't needed to test its tiering logic."""

    def __init__(self, full_name="Chidi Okafor", profession="Plumber", bio=None, category_id=1, skills=None):
        self.user = _FakeUser(full_name)
        self.profession = profession
        self.bio = bio
        self.category_id = category_id
        self.skills = skills or []


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


# ---------------------------------------------------------------------------
# text_relevance_score: tiered relevance (Stage 2)
# ---------------------------------------------------------------------------


def test_relevance_score_is_zero_with_no_query():
    professional = _FakeProfessional()
    assert text_relevance_score(professional, "") == RELEVANCE_NO_MATCH
    assert text_relevance_score(professional, "   ") == RELEVANCE_NO_MATCH


def test_relevance_score_exact_name_match():
    professional = _FakeProfessional(full_name="Chidi Okafor")
    assert text_relevance_score(professional, "Chidi Okafor") == RELEVANCE_EXACT_NAME


def test_relevance_score_exact_profession_match():
    professional = _FakeProfessional(profession="Plumber")
    assert text_relevance_score(professional, "Plumber") == RELEVANCE_EXACT_PROFESSION


def test_relevance_score_partial_profession_match():
    professional = _FakeProfessional(profession="Master Plumber")
    assert text_relevance_score(professional, "plumber") == RELEVANCE_PROFESSION_MATCH


def test_relevance_score_category_match():
    professional = _FakeProfessional(profession="Wiring Specialist", category_id=7)
    assert text_relevance_score(professional, "electrician", matching_category_ids={7}) == RELEVANCE_CATEGORY_MATCH


def test_relevance_score_skill_match():
    professional = _FakeProfessional(profession="Handyman", skills=[_FakeSkill("Solar Installation")])
    assert text_relevance_score(professional, "solar") == RELEVANCE_SKILL_MATCH


def test_relevance_score_bio_match_is_the_weakest_real_match():
    professional = _FakeProfessional(profession="Handyman", bio="I once fixed a generator too.")
    assert text_relevance_score(professional, "generator") == RELEVANCE_BIO_MATCH


def test_relevance_score_name_substring_match():
    professional = _FakeProfessional(full_name="Chidi Okafor Electrical Services")
    assert text_relevance_score(professional, "Okafor") == RELEVANCE_NAME_MATCH


def test_relevance_score_no_match_returns_zero():
    professional = _FakeProfessional(profession="Plumber", bio="Reliable plumbing services.")
    assert text_relevance_score(professional, "photography") == RELEVANCE_NO_MATCH


def test_relevance_score_tiers_are_strictly_ordered():
    # A single professional who matches at every tier simultaneously must
    # score by the *strongest* tier, not the weakest or a sum of them.
    professional = _FakeProfessional(
        full_name="Ada Plumber",
        profession="Plumber",
        bio="I do plumber-related work.",
        category_id=3,
        skills=[_FakeSkill("Plumber Certification")],
    )
    assert text_relevance_score(professional, "Plumber", matching_category_ids={3}) == RELEVANCE_EXACT_PROFESSION
    assert RELEVANCE_EXACT_NAME > RELEVANCE_EXACT_PROFESSION > RELEVANCE_PROFESSION_MATCH
    assert RELEVANCE_PROFESSION_MATCH > RELEVANCE_CATEGORY_MATCH > RELEVANCE_SKILL_MATCH
    assert RELEVANCE_SKILL_MATCH > RELEVANCE_NAME_MATCH > RELEVANCE_BIO_MATCH > RELEVANCE_NO_MATCH
