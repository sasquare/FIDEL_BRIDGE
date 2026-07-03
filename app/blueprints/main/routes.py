from flask import jsonify, render_template
from sqlalchemy import func

from app.blueprints.main import main_bp
from app.extensions import db, limiter
from app.models.booking import STATUS_COMPLETED, Booking
from app.models.category import Category
from app.models.professional import ProfessionalProfile
from app.models.review import Review


@main_bp.route("/")
def index():
    # Capped generously above the current catalog size (18 as of this
    # writing) so newly-added categories don't silently push existing ones
    # off the homepage purely due to alphabetical ordering. "View All
    # Categories" below remains the overflow escape hatch once it's exceeded.
    categories = Category.query.order_by(Category.name).limit(24).all()
    category_ids = [category.id for category in categories]

    professional_counts = dict(
        db.session.query(ProfessionalProfile.category_id, func.count(ProfessionalProfile.id))
        .filter(ProfessionalProfile.category_id.in_(category_ids))
        .group_by(ProfessionalProfile.category_id)
        .all()
    )
    average_ratings = dict(
        db.session.query(ProfessionalProfile.category_id, func.avg(Review.rating))
        .join(Review, Review.professional_profile_id == ProfessionalProfile.id)
        .filter(ProfessionalProfile.category_id.in_(category_ids))
        .group_by(ProfessionalProfile.category_id)
        .all()
    )

    # Attached as plain Python attributes (not DB columns) so the template
    # can read real counts/ratings without an extra query per card.
    for category in categories:
        category.professional_count = professional_counts.get(category.id, 0)
        avg = average_ratings.get(category.id)
        category.average_rating = round(avg, 1) if avg is not None else None

    average_rating = db.session.query(func.avg(Review.rating)).scalar()
    stats = {
        "verified_professionals": ProfessionalProfile.query.filter_by(is_verified=True).count(),
        "completed_jobs": Booking.query.filter_by(status=STATUS_COMPLETED).count(),
        "total_reviews": Review.query.count(),
        "average_rating": f"{average_rating:.1f}" if average_rating is not None else "—",
    }

    return render_template("main/index.html", categories=categories, stats=stats)


@main_bp.route("/healthz")
@limiter.exempt
def healthz():
    """Liveness endpoint for Render's health check and uptime monitors."""
    return jsonify(status="ok"), 200
