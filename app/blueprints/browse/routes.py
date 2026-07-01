from flask import render_template, request
from sqlalchemy import or_, select

from app.blueprints.browse import browse_bp
from app.extensions import db
from app.models import roles
from app.models.category import Category
from app.models.professional import ProfessionalProfile
from app.models.skill import Skill
from app.models.user import User

PER_PAGE = 12


@browse_bp.route("/categories")
def categories():
    all_categories = Category.query.order_by(Category.name).all()
    return render_template("browse/categories.html", categories=all_categories)


@browse_bp.route("/professionals")
def professionals():
    category_slug = request.args.get("category", "").strip()
    city = request.args.get("city", "").strip()
    query_text = request.args.get("q", "").strip()
    page = request.args.get("page", 1, type=int)

    stmt = (
        select(ProfessionalProfile)
        .join(User, ProfessionalProfile.user_id == User.id)
        .where(User.role == roles.PROFESSIONAL, User.is_active_account.is_(True))
    )

    active_category = None
    if category_slug:
        active_category = Category.query.filter_by(slug=category_slug).first()
        if active_category:
            stmt = stmt.where(ProfessionalProfile.category_id == active_category.id)

    if city:
        stmt = stmt.where(ProfessionalProfile.city.ilike(f"%{city}%"))

    if query_text:
        like = f"%{query_text}%"
        stmt = stmt.where(
            or_(
                User.full_name.ilike(like),
                ProfessionalProfile.profession.ilike(like),
                ProfessionalProfile.bio.ilike(like),
                ProfessionalProfile.id.in_(select(Skill.professional_profile_id).where(Skill.name.ilike(like))),
            )
        )

    stmt = stmt.order_by(ProfessionalProfile.is_verified.desc(), ProfessionalProfile.created_at.desc())

    pagination = db.paginate(stmt, page=page, per_page=PER_PAGE, error_out=False)

    return render_template(
        "browse/professionals.html",
        pagination=pagination,
        professionals=pagination.items,
        categories=Category.query.order_by(Category.name).all(),
        active_category=active_category,
        filters={"category": category_slug, "city": city, "q": query_text},
    )


@browse_bp.route("/professionals/<int:user_id>")
def professional_profile(user_id):
    professional = (
        ProfessionalProfile.query.join(User)
        .filter(User.id == user_id, User.role == roles.PROFESSIONAL)
        .first_or_404()
    )
    return render_template("browse/professional_profile.html", professional=professional)
