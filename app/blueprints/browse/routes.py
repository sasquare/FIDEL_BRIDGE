from flask import render_template, request
from sqlalchemy import func, or_, select

from app.blueprints.browse import browse_bp
from app.extensions import db
from app.models import roles
from app.models.category import Category
from app.models.professional import ProfessionalProfile
from app.models.review import Review
from app.models.skill import Skill
from app.models.user import User

PER_PAGE = 12

SORT_OPTIONS = [
    ("relevance", "Most Relevant"),
    ("rating", "Highest Rated"),
    ("reviews", "Most Reviews"),
    ("newest", "Newest"),
]
MIN_RATING_OPTIONS = [("", "Any Rating"), ("4", "4+ Stars"), ("3", "3+ Stars")]


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
    elif sort_by == "reviews":
        stmt = stmt.order_by(rating_subq.c.review_count.desc().nulls_last(), ProfessionalProfile.created_at.desc())
    elif sort_by == "newest":
        stmt = stmt.order_by(ProfessionalProfile.created_at.desc())
    else:
        sort_by = "relevance"
        stmt = stmt.order_by(ProfessionalProfile.is_verified.desc(), ProfessionalProfile.created_at.desc())

    pagination = db.paginate(stmt, page=page, per_page=PER_PAGE, error_out=False)

    return render_template(
        "browse/professionals.html",
        pagination=pagination,
        professionals=pagination.items,
        categories=Category.query.order_by(Category.name).all(),
        active_category=active_category,
        sort_options=SORT_OPTIONS,
        min_rating_options=MIN_RATING_OPTIONS,
        filters={
            "category": category_slug,
            "city": city,
            "state": state,
            "q": query_text,
            "min_rating": min_rating,
            "sort": sort_by,
        },
    )


@browse_bp.route("/professionals/<int:user_id>")
def professional_profile(user_id):
    professional = (
        ProfessionalProfile.query.join(User)
        .filter(User.id == user_id, User.role == roles.PROFESSIONAL)
        .first_or_404()
    )
    return render_template("browse/professional_profile.html", professional=professional)
