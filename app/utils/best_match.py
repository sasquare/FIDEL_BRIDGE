"""Best Match: the composite ranking score behind the "Most Relevant"
sort on search results.

Built as a staged pipeline rather than one weighted formula - each stage
answers a different question, can be tested and tuned independently, and
can eventually be replaced (by a smarter formula, or a learned model)
without touching the others. See the Best Match design document for the
full architecture:

    Stage 0  Candidate Generation  - existing search filters (Phases 1-2)
    Stage 1  Eligibility           - hard gates (already enforced by the
                                      is_active_account filter in the
                                      candidate query)
    Stage 2  Text Relevance        - text_relevance_score()
    Stage 3  Trust & Quality       - quality_score()
    Stage 4  Context Matching      - context_score()
    Stage 5  Composite             - best_match_score()

Badges (customer-facing "Best Match" / "Top Rated" / etc. indicators,
never a raw score) live in app/utils/badges.py, built from these same
signals rather than a parallel calculation.
"""
from datetime import datetime, timezone

# Tiered, not a flat "matches or doesn't": an exact profession match is a
# much stronger relevance signal than a keyword that merely happens to
# appear somewhere in a long bio, and the score must reflect that or
# "Most Relevant" isn't actually ranking by relevance.
RELEVANCE_EXACT_NAME = 100
RELEVANCE_EXACT_PROFESSION = 95
RELEVANCE_PROFESSION_MATCH = 80
RELEVANCE_CATEGORY_MATCH = 70
RELEVANCE_SKILL_MATCH = 60
RELEVANCE_NAME_MATCH = 50
RELEVANCE_BIO_MATCH = 30
RELEVANCE_NO_MATCH = 0


def text_relevance_score(professional, query_text, matching_category_ids=frozenset()):
    """Tiered relevance score (0-100) for how well a professional matches
    a customer's free-text search.

    matching_category_ids should be the set of Category.id values whose
    name matches query_text (computed once per search, not per
    professional - see browse/routes.py).

    professional.user and professional.skills must already be loaded
    (e.g. via selectinload) before calling this across a batch of
    professionals, or each call becomes its own extra query.
    """
    if not query_text:
        return RELEVANCE_NO_MATCH

    query_lower = query_text.strip().lower()
    if not query_lower:
        return RELEVANCE_NO_MATCH

    full_name = (professional.user.full_name or "").lower()
    profession = (professional.profession or "").lower()
    bio = (professional.bio or "").lower()

    if full_name == query_lower:
        return RELEVANCE_EXACT_NAME
    if profession == query_lower:
        return RELEVANCE_EXACT_PROFESSION
    if query_lower in profession:
        return RELEVANCE_PROFESSION_MATCH
    if professional.category_id in matching_category_ids:
        return RELEVANCE_CATEGORY_MATCH
    if any(query_lower in skill.name.lower() for skill in professional.skills):
        return RELEVANCE_SKILL_MATCH
    if query_lower in full_name:
        return RELEVANCE_NAME_MATCH
    if bio and query_lower in bio:
        return RELEVANCE_BIO_MATCH
    return RELEVANCE_NO_MATCH


# ---------------------------------------------------------------------------
# Stage 3: Trust & Quality
# ---------------------------------------------------------------------------

# Trust Score already blends verification, rating, review volume, completed
# jobs and profile completion into one 0-100 number - it stays the dominant
# input here rather than being re-derived, so there is exactly one place
# (app/utils/trust_score.py) that defines what "trustworthy" means on
# FidelBridge. Response time and recent activity are the two signals Best
# Match adds on top: neither belongs in Trust Score itself (Trust Score is
# shown and used elsewhere - dashboards, admin, the public profile - where
# "how fast do you reply" and "are you still active" aren't the point).
QUALITY_WEIGHTS = {
    "trust_score": 70,
    "response_time": 15,
    "recent_activity": 15,
}

# A newly-verified professional with zero reviews gets a temporary,
# decaying boost so they aren't invisible until their first booking somehow
# happens despite that invisibility - the cold-start "death spiral"
# described in the design document. Deliberately time-boxed and cleared the
# moment a real review arrives, since real signal should always outrank a
# temporary courtesy boost.
COLD_START_BOOST_DAYS = 30
COLD_START_BOOST_POINTS = 15


def response_time_score(professional):
    """0-100 based on average response time to booking requests. No data
    yet scores as neutral (50), not zero - the same "unproven, not bad"
    principle used for ratings (see app/utils/rating.py)."""
    minutes = professional.average_response_minutes
    if minutes is None:
        return 50
    if minutes <= 60:
        return 100
    if minutes <= 4 * 60:
        return 80
    if minutes <= 24 * 60:
        return 60
    if minutes <= 3 * 24 * 60:
        return 35
    return 15


def as_aware_utc(value):
    """SQLite strips tzinfo on storage, so a datetime read back from the DB
    is naive even though it was written via datetime.now(timezone.utc) -
    same quirk already handled in User.query_by_valid_reset_token. Values
    passed directly in tests are already aware and pass through unchanged.
    Public (not prefixed) since app/utils/badges.py needs the same fix."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def recent_activity_score(professional, now=None):
    """0-100 based on how recently the professional had any booking
    activity. No data yet scores as neutral (50), not zero - a
    professional who just joined hasn't had the chance to be "recently
    active" in booking terms yet, which isn't the same as being dormant."""
    now = now or datetime.now(timezone.utc)
    last_active = professional.last_active_at
    if last_active is None:
        return 50
    days = (now - as_aware_utc(last_active)).total_seconds() / 86400
    if days <= 7:
        return 100
    if days <= 30:
        return 65
    if days <= 90:
        return 30
    return 10


def cold_start_boost(professional, now=None):
    """Temporary points added on top of the weighted quality score for a
    newly-verified professional with no reviews yet. Zero once
    COLD_START_BOOST_DAYS have passed since verification, or the instant
    they earn their first review - whichever comes first."""
    if not professional.is_verified or professional.verified_at is None:
        return 0
    if professional.review_count > 0:
        return 0

    now = now or datetime.now(timezone.utc)
    days_since_verified = (now - as_aware_utc(professional.verified_at)).total_seconds() / 86400
    if days_since_verified > COLD_START_BOOST_DAYS:
        return 0
    return COLD_START_BOOST_POINTS


def quality_score(professional, now=None):
    """Stage 3: query-independent professional quality. Can exceed 100
    while the cold-start boost is active - intentional, so a newly-
    verified professional can meaningfully compete against established
    professionals with weaker quality signals during their boost window,
    not merely narrow the gap."""
    weights = QUALITY_WEIGHTS
    score = (
        (professional.trust_score / 100) * weights["trust_score"]
        + (response_time_score(professional) / 100) * weights["response_time"]
        + (recent_activity_score(professional, now) / 100) * weights["recent_activity"]
    )
    score += cold_start_boost(professional, now)
    return round(score)


# ---------------------------------------------------------------------------
# Stage 4: Context Matching
# ---------------------------------------------------------------------------

# Location: graduated, not binary, because the SQL filter behind it (Phase
# 1's city/state ILIKE) is a substring match - "Lagos" also matches "Lagos
# Island" or "New Lagos Estate". Everyone in the candidate pool already
# satisfied that filter (Stage 0), so this only differentiates an exact
# match from a looser one within an already-filtered pool - it does not
# (yet) do real geo-distance ranking. True budget-fit scoring for pricing
# needs a customer-side budget input that doesn't exist yet either (see the
# design doc) - this stays a weak "has pricing info at all" signal until
# that lands.
LOCATION_EXACT_MATCH = 100
LOCATION_PARTIAL_MATCH = 75
LOCATION_NO_SIGNAL = 50  # no location filter applied - neutral, not a penalty
PRICING_INFO_PRESENT = 70
PRICING_INFO_ABSENT = 40

CONTEXT_WEIGHTS = {
    "location": 60,
    "pricing": 40,
}


def location_relevance_score(professional, city_filter=None, state_filter=None):
    """0-100. No location filter at all is neutral (50) - Best Match
    shouldn't invent a location preference the customer never expressed."""
    if not city_filter and not state_filter:
        return LOCATION_NO_SIGNAL

    professional_city = (professional.city or "").strip().lower()
    professional_state = (professional.state or "").strip().lower()

    if city_filter and professional_city == city_filter.strip().lower():
        return LOCATION_EXACT_MATCH
    if state_filter and professional_state == state_filter.strip().lower():
        return LOCATION_EXACT_MATCH
    return LOCATION_PARTIAL_MATCH


def pricing_suitability_score(professional):
    """0-100. A weak signal only (see module docstring) - rewards simply
    having pricing information at all, since it reduces back-and-forth
    regardless of the specific amount."""
    if professional.pricing_summary or professional.consultation_fee:
        return PRICING_INFO_PRESENT
    return PRICING_INFO_ABSENT


def context_score(professional, city_filter=None, state_filter=None):
    """Stage 4: fit that depends on this customer's search, beyond plain
    text relevance - currently location and pricing; personalization is
    the natural future occupant of this stage (see the design doc)."""
    weights = CONTEXT_WEIGHTS
    score = (
        (location_relevance_score(professional, city_filter, state_filter) / 100) * weights["location"]
        + (pricing_suitability_score(professional) / 100) * weights["pricing"]
    )
    return round(score)


# ---------------------------------------------------------------------------
# Stage 5: Composite
# ---------------------------------------------------------------------------

# Relevance is weighted highest, per the design doc's stated priority order
# (relevance is close to non-negotiable - a highly trusted plumber is not a
# good match for "wedding photographer"). When there's no query text,
# relevance is 0 for every candidate uniformly, so it drops out of the
# comparison entirely and ranking is driven by quality + context alone -
# exactly the desired "browsing without a keyword" behavior, with no
# special-casing required.
BEST_MATCH_WEIGHTS = {
    "relevance": 50,
    "quality": 35,
    "context": 15,
}


def best_match_score(professional, query_text, matching_category_ids=frozenset(), city_filter=None, state_filter=None, now=None):
    """Stage 5: the final composite score behind the "Most Relevant" sort.
    Higher is better; not bounded to 0-100 since quality_score's cold-start
    boost can push slightly past it (intentional - see quality_score)."""
    weights = BEST_MATCH_WEIGHTS
    relevance = text_relevance_score(professional, query_text, matching_category_ids)
    quality = quality_score(professional, now=now)
    context = context_score(professional, city_filter=city_filter, state_filter=state_filter)

    composite = (
        (relevance / 100) * weights["relevance"]
        + (quality / 100) * weights["quality"]
        + (context / 100) * weights["context"]
    )
    return round(composite, 2)
