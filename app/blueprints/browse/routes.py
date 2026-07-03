from flask import render_template, request
from flask_sqlalchemy.pagination import Pagination
from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload

from app.blueprints.browse import browse_bp
from app.extensions import db
from app.models import roles
from app.models.category import Category
from app.models.professional import ProfessionalProfile
from app.models.review import Review
from app.models.skill import Skill
from app.models.user import User
from app.utils.badges import compute_badges
from app.utils.best_match import best_match_score, quality_score

PER_PAGE = 12

# How many SQL-filtered candidates get fully scored in Python for the
# "Most Relevant" (Best Match) sort - see _rank_by_best_match below for why
# this can't be a single ORDER BY. Generous relative to today's actual
# professional counts; the honest tradeoff is that a candidate ranked
# below this cutoff by the cheap SQL pre-sort never gets a chance at
# Python scoring, however strong its true relevance. Revisit once
# real volume approaches this number (see the design doc's Future
# Evolution section on Postgres full-text search).
BEST_MATCH_CANDIDATE_POOL_CAP = 500

# "Best Match" is a rank-derived badge (the #1 result of this specific
# search), not a threshold badge like the others in app/utils/badges.py -
# but it still must clear an absolute quality floor, or it ends up
# labeling a technically-top-of-a-weak-list result as if it were
# genuinely excellent. 50 is calibrated against quality_score's own
# neutral defaults: an unverified professional with zero track record
# tops out around 43 even with a complete profile, while any verified
# professional starts above 53 before a single review or completed job -
# so this floor requires at least verification, but doesn't require an
# established track record (a newly-verified professional inside their
# cold-start window can still qualify).
BEST_MATCH_MIN_QUALITY = 50

SORT_OPTIONS = [
    ("relevance", "Most Relevant"),
    ("rating", "Highest Rated"),
    ("reviews", "Most Reviews"),
    ("newest", "Newest"),
]
MIN_RATING_OPTIONS = [("", "Any Rating"), ("4", "4+ Stars"), ("3", "3+ Stars")]


class _PrecomputedPagination(Pagination):
    """A Pagination-compatible object built from an already-sorted,
    already-sliced Python list, instead of running a fresh SQL query.

    Best Match's composite score (app/utils/best_match.py) can't be
    expressed as a single ORDER BY - it blends a SQL-computed candidate
    pool with several Python-computed signals - so db.paginate() isn't an
    option for that sort. This reuses Pagination's existing .pages/
    .iter_pages() math (both pure functions of .total/.page/.per_page)
    so the template needs no special-casing between the two code paths.
    """

    def __init__(self, *, page, per_page, total, items):
        self._items = items
        self._total = total
        super().__init__(page=page, per_page=per_page, max_per_page=None, error_out=False, count=True)

    def _query_items(self):
        return self._items

    def _query_count(self):
        return self._total


def _attach_rating_summary(professionals):
    """Attach search_average_rating/search_review_count as plain Python
    attributes (not DB columns - same pattern as the category stats in
    main/routes.py) computed via a single grouped aggregate query.

    Deliberately NOT using ProfessionalProfile.average_rating/review_count
    here: those properties compute from professional.reviews, which lazy-
    loads every Review row (including comment text) per professional - an
    N+1 that's invisible with one professional in the DB but real once
    there are hundreds. One extra query for the whole page, vs. one per
    card, regardless of page size.
    """
    professional_ids = [p.id for p in professionals]
    if not professional_ids:
        return

    rating_rows = (
        db.session.query(
            Review.professional_profile_id,
            func.avg(Review.rating).label("avg_rating"),
            func.count(Review.id).label("review_count"),
        )
        .filter(Review.professional_profile_id.in_(professional_ids))
        .group_by(Review.professional_profile_id)
        .all()
    )
    ratings_by_id = {row.professional_profile_id: row for row in rating_rows}

    for professional in professionals:
        row = ratings_by_id.get(professional.id)
        professional.search_average_rating = float(row.avg_rating) if row else None
        professional.search_review_count = row.review_count if row else 0


def _matching_category_ids(query_text):
    """Category IDs whose name matches query_text - computed once per
    search (not per professional) for Stage 2's category-match tier."""
    if not query_text:
        return frozenset()
    like = f"%{query_text}%"
    rows = db.session.query(Category.id).filter(Category.name.ilike(like)).all()
    return frozenset(cid for (cid,) in rows)


def _rank_by_best_match(stmt, *, query_text, city, state, page):
    """Fetch a bounded SQL-filtered candidate pool, score each candidate
    with the Best Match composite in Python, and return a page of results
    as a _PrecomputedPagination.

    Mirrors the pattern already used for the homepage's Featured
    Professionals (selectinload a bounded pool, sort in Python) - Best
    Match's composite blends a SQL-computed relevance filter with several
    Python-computed quality/context signals from app/utils/best_match.py,
    which can't be expressed as one ORDER BY without duplicating that
    logic in SQL and risking it drifting out of sync with the Python
    version used everywhere else (dashboard, admin, public profile).
    """
    candidate_stmt = (
        stmt.order_by(ProfessionalProfile.is_verified.desc(), ProfessionalProfile.created_at.desc())
        .limit(BEST_MATCH_CANDIDATE_POOL_CAP)
        .options(
            # quality_score() reaches into trust_score (reviews, bookings),
            # profile_completion_percentage (skills, portfolio_items,
            # verifications), and response/activity scoring (bookings) - if
            # any of these aren't eager-loaded here, scoring the candidate
            # pool reintroduces exactly the N+1 Phase 1 removed from the
            # rating display, just for a different set of relationships.
            selectinload(ProfessionalProfile.user),
            selectinload(ProfessionalProfile.skills),
            selectinload(ProfessionalProfile.reviews),
            selectinload(ProfessionalProfile.bookings),
            selectinload(ProfessionalProfile.portfolio_items),
            selectinload(ProfessionalProfile.verifications),
        )
    )
    candidates = list(db.session.execute(candidate_stmt).scalars().all())
    _attach_rating_summary(candidates)

    matching_category_ids = _matching_category_ids(query_text)
    for candidate in candidates:
        candidate.best_match_score = best_match_score(
            candidate,
            query_text,
            matching_category_ids=matching_category_ids,
            city_filter=city or None,
            state_filter=state or None,
        )
    candidates.sort(key=lambda c: c.best_match_score, reverse=True)

    page = max(page, 1)
    start = (page - 1) * PER_PAGE
    page_items = candidates[start : start + PER_PAGE]

    # Badges are a pure display concern - computed only for the page being
    # rendered, not the whole candidate pool, since they never influence
    # ranking. "Best Match" is added here (not in app/utils/badges.py)
    # because it's rank-derived: true only for the single #1 result of
    # this specific search, and only on page 1 - it wouldn't mean
    # anything attached to the first item of page 3.
    for item in page_items:
        item.badges = compute_badges(item)
    if page == 1 and page_items and quality_score(page_items[0]) >= BEST_MATCH_MIN_QUALITY:
        page_items[0].badges = ["best_match"] + page_items[0].badges

    return _PrecomputedPagination(page=page, per_page=PER_PAGE, total=len(candidates), items=page_items)


def _build_active_filters(filters, active_category):
    """Build removable filter chips for the search results page.

    Each chip carries the current filter set with just that one key
    cleared, so removing a chip is a single link click that preserves
    every other filter. Sort is deliberately excluded: it's an ordering
    preference, not a constraint that narrows the result set, so "remove"
    doesn't apply to it the way it does to a keyword or location filter.
    """
    min_rating_labels = dict(MIN_RATING_OPTIONS)
    chips = []

    def add(key, label):
        remaining = {**filters, key: ""}
        chips.append({"key": key, "label": label, "remove_args": {k: v for k, v in remaining.items() if v}})

    if filters["q"]:
        add("q", f'"{filters["q"]}"')
    if active_category:
        add("category", active_category.name)
    if filters["city"]:
        add("city", filters["city"])
    if filters["state"]:
        add("state", filters["state"])
    if filters["min_rating"]:
        add("min_rating", min_rating_labels.get(filters["min_rating"], filters["min_rating"]))

    return chips


def _build_recovery_suggestions(active_category):
    """Categories that currently have at least one active professional,
    for the empty-results recovery UI - excludes the active category
    (if any) since re-suggesting the exact search that just came up empty
    isn't a recovery path. Ordered by professional count, so the
    suggestions point toward categories most likely to actually help.
    """
    query = (
        db.session.query(Category, func.count(ProfessionalProfile.id).label("count"))
        .join(ProfessionalProfile, ProfessionalProfile.category_id == Category.id)
        .join(User, ProfessionalProfile.user_id == User.id)
        .filter(User.role == roles.PROFESSIONAL, User.is_active_account.is_(True))
    )
    if active_category:
        query = query.filter(Category.id != active_category.id)

    rows = query.group_by(Category.id).order_by(func.count(ProfessionalProfile.id).desc()).limit(5).all()
    return [category for category, _count in rows]


@browse_bp.route("/categories")
def categories():
    all_categories = Category.query.order_by(Category.name).all()
    return render_template("browse/categories.html", categories=all_categories)


@browse_bp.route("/professionals")
def professionals():
    category_slug = request.args.get("category", "").strip()
    city = request.args.get("city", "").strip()
    state = request.args.get("state", "").strip()
    query_text = request.args.get("q", "").strip()
    min_rating = request.args.get("min_rating", "").strip()
    sort_by = request.args.get("sort", "relevance").strip()
    page = request.args.get("page", 1, type=int)

    rating_subq = (
        db.session.query(
            Review.professional_profile_id.label("professional_profile_id"),
            func.avg(Review.rating).label("avg_rating"),
            func.count(Review.id).label("review_count"),
        )
        .group_by(Review.professional_profile_id)
        .subquery()
    )

    stmt = (
        select(ProfessionalProfile)
        .join(User, ProfessionalProfile.user_id == User.id)
        .outerjoin(rating_subq, ProfessionalProfile.id == rating_subq.c.professional_profile_id)
        .where(User.role == roles.PROFESSIONAL, User.is_active_account.is_(True))
    )

    active_category = None
    if category_slug:
        active_category = Category.query.filter_by(slug=category_slug).first()
        if active_category:
            stmt = stmt.where(ProfessionalProfile.category_id == active_category.id)

    if city:
        stmt = stmt.where(ProfessionalProfile.city.ilike(f"%{city}%"))

    if state:
        stmt = stmt.where(ProfessionalProfile.state.ilike(f"%{state}%"))

    if query_text:
        like = f"%{query_text}%"
        stmt = stmt.where(
            or_(
                User.full_name.ilike(like),
                ProfessionalProfile.profession.ilike(like),
                ProfessionalProfile.bio.ilike(like),
                ProfessionalProfile.id.in_(select(Skill.professional_profile_id).where(Skill.name.ilike(like))),
                # The homepage search bar's autocomplete suggests category
                # names (see hero-categories datalist in main/index.html) -
                # without this, picking a suggestion like "Plumbing" would
                # return zero results unless some professional's own
                # profession/bio/skill text happened to contain that word.
                ProfessionalProfile.category_id.in_(select(Category.id).where(Category.name.ilike(like))),
            )
        )

    if min_rating:
        stmt = stmt.where(rating_subq.c.avg_rating >= float(min_rating))

    if sort_by == "rating":
        stmt = stmt.order_by(rating_subq.c.avg_rating.desc().nulls_last(), ProfessionalProfile.created_at.desc())
        pagination = db.paginate(stmt, page=page, per_page=PER_PAGE, error_out=False)
        _attach_rating_summary(pagination.items)
    elif sort_by == "reviews":
        stmt = stmt.order_by(rating_subq.c.review_count.desc().nulls_last(), ProfessionalProfile.created_at.desc())
        pagination = db.paginate(stmt, page=page, per_page=PER_PAGE, error_out=False)
        _attach_rating_summary(pagination.items)
    elif sort_by == "newest":
        stmt = stmt.order_by(ProfessionalProfile.created_at.desc())
        pagination = db.paginate(stmt, page=page, per_page=PER_PAGE, error_out=False)
        _attach_rating_summary(pagination.items)
    else:
        # "relevance" (the default / Best Match): rating/reviews/newest are
        # explicit, honest single-signal overrides a customer can choose,
        # left exactly as they were - only the default sort is powered by
        # the Best Match composite.
        sort_by = "relevance"
        pagination = _rank_by_best_match(stmt, query_text=query_text, city=city, state=state, page=page)

    filters = {
        "category": category_slug,
        "city": city,
        "state": state,
        "q": query_text,
        "min_rating": min_rating,
        "sort": sort_by,
    }
    active_filters = _build_active_filters(filters, active_category)

    # Recovery suggestions only matter when the search actually came up
    # empty and some filter narrowed it there - no point suggesting
    # "browse another category" when the whole platform has no
    # professionals yet, or when the customer already sees results.
    recovery_categories = []
    if pagination.total == 0 and active_filters:
        recovery_categories = _build_recovery_suggestions(active_category)

    return render_template(
        "browse/professionals.html",
        pagination=pagination,
        professionals=pagination.items,
        categories=Category.query.order_by(Category.name).all(),
        active_category=active_category,
        sort_options=SORT_OPTIONS,
        min_rating_options=MIN_RATING_OPTIONS,
        filters=filters,
        active_filters=active_filters,
        recovery_categories=recovery_categories,
    )


@browse_bp.route("/professionals/<int:user_id>")
def professional_profile(user_id):
    professional = (
        ProfessionalProfile.query.join(User)
        .filter(User.id == user_id, User.role == roles.PROFESSIONAL)
        .first_or_404()
    )
    return render_template("browse/professional_profile.html", professional=professional)
