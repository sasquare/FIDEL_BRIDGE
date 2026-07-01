from flask import abort, current_app, flash, redirect, render_template, send_from_directory, url_for
from flask_login import current_user
from flask_wtf import FlaskForm

from app.blueprints.professional import professional_bp
from app.extensions import db
from app.forms.professional import PortfolioItemForm, ProfessionalProfileForm, SkillForm, VerificationUploadForm
from app.models import roles
from app.models.category import Category
from app.models.portfolio import PortfolioItem
from app.models.skill import Skill
from app.models.verification import Verification
from app.utils.decorators import role_required
from app.utils.uploads import save_portfolio_image, save_verification_document


def _sidebar_items():
    return [
        {"key": "dashboard", "label": "Dashboard", "url": url_for("professional.dashboard")},
        {"key": "profile", "label": "My Profile", "url": url_for("professional.profile")},
        {"key": "skills", "label": "Skills", "url": url_for("professional.skills")},
        {"key": "portfolio", "label": "Portfolio", "url": url_for("professional.portfolio")},
        {"key": "verification", "label": "Verification", "url": url_for("professional.verification")},
    ]


def _current_professional():
    return current_user.professional_profile


@professional_bp.route("/dashboard")
@role_required(roles.PROFESSIONAL)
def dashboard():
    professional = _current_professional()
    return render_template(
        "professional/dashboard.html",
        user=current_user,
        professional=professional,
        active="dashboard",
        sidebar_items=_sidebar_items(),
    )


@professional_bp.route("/profile", methods=["GET", "POST"])
@role_required(roles.PROFESSIONAL)
def profile():
    professional = _current_professional()
    # Built from explicit kwargs rather than obj=professional: WTForms gives
    # obj attributes priority over kwargs whenever the attribute exists, and
    # professional.available_days is a raw comma-string (not the list shape
    # the checkbox field needs), which would silently show every box unchecked.
    form = ProfessionalProfileForm(
        profession=professional.profession,
        category_id=professional.category_id,
        city=professional.city,
        state=professional.state,
        years_experience=professional.years_experience,
        bio=professional.bio,
        available_days=professional.available_days_list,
        available_hours=professional.available_hours,
    )
    form.category_id.choices = [
        (category.id, category.name) for category in Category.query.order_by(Category.name).all()
    ]

    if form.validate_on_submit():
        professional.profession = form.profession.data.strip()
        professional.category_id = form.category_id.data
        professional.city = form.city.data.strip() if form.city.data else None
        professional.state = form.state.data.strip() if form.state.data else None
        professional.years_experience = form.years_experience.data
        professional.bio = form.bio.data.strip() if form.bio.data else None
        professional.available_days = ",".join(form.available_days.data)
        professional.available_hours = form.available_hours.data.strip() if form.available_hours.data else None

        db.session.commit()
        flash("Your profile has been updated.", "success")
        return redirect(url_for("professional.profile"))

    return render_template(
        "professional/profile.html", form=form, active="profile", sidebar_items=_sidebar_items()
    )


@professional_bp.route("/skills", methods=["GET", "POST"])
@role_required(roles.PROFESSIONAL)
def skills():
    professional = _current_professional()
    form = SkillForm()
    delete_form = FlaskForm()

    if form.validate_on_submit():
        db.session.add(Skill(professional_profile_id=professional.id, name=form.name.data.strip()))
        db.session.commit()
        flash("Skill added.", "success")
        return redirect(url_for("professional.skills"))

    return render_template(
        "professional/skills.html",
        form=form,
        delete_form=delete_form,
        skills=professional.skills,
        active="skills",
        sidebar_items=_sidebar_items(),
    )


@professional_bp.route("/skills/<int:skill_id>/delete", methods=["POST"])
@role_required(roles.PROFESSIONAL)
def delete_skill(skill_id):
    professional = _current_professional()
    skill = Skill.query.filter_by(id=skill_id, professional_profile_id=professional.id).first_or_404()
    db.session.delete(skill)
    db.session.commit()
    flash("Skill removed.", "success")
    return redirect(url_for("professional.skills"))


@professional_bp.route("/portfolio", methods=["GET", "POST"])
@role_required(roles.PROFESSIONAL)
def portfolio():
    professional = _current_professional()
    form = PortfolioItemForm()
    delete_form = FlaskForm()

    if form.validate_on_submit():
        image_filename = None
        if form.image.data:
            image_filename = save_portfolio_image(form.image.data, current_user.id)

        db.session.add(
            PortfolioItem(
                professional_profile_id=professional.id,
                title=form.title.data.strip(),
                description=form.description.data.strip() if form.description.data else None,
                image_filename=image_filename,
            )
        )
        db.session.commit()
        flash("Portfolio item added.", "success")
        return redirect(url_for("professional.portfolio"))

    return render_template(
        "professional/portfolio.html",
        form=form,
        delete_form=delete_form,
        portfolio_items=professional.portfolio_items,
        active="portfolio",
        sidebar_items=_sidebar_items(),
    )


@professional_bp.route("/portfolio/<int:item_id>/delete", methods=["POST"])
@role_required(roles.PROFESSIONAL)
def delete_portfolio_item(item_id):
    professional = _current_professional()
    item = PortfolioItem.query.filter_by(id=item_id, professional_profile_id=professional.id).first_or_404()
    db.session.delete(item)
    db.session.commit()
    flash("Portfolio item removed.", "success")
    return redirect(url_for("professional.portfolio"))


@professional_bp.route("/verification", methods=["GET", "POST"])
@role_required(roles.PROFESSIONAL)
def verification():
    professional = _current_professional()
    form = VerificationUploadForm()

    if form.validate_on_submit():
        try:
            filename = save_verification_document(form.file.data, current_user.id)
        except ValueError:
            flash("That file type isn't supported.", "error")
        else:
            db.session.add(
                Verification(
                    professional_profile_id=professional.id,
                    document_type=form.document_type.data,
                    filename=filename,
                )
            )
            db.session.commit()
            flash("Document uploaded and pending review.", "success")
        return redirect(url_for("professional.verification"))

    return render_template(
        "professional/verification.html",
        form=form,
        verifications=professional.verifications,
        active="verification",
        sidebar_items=_sidebar_items(),
    )


@professional_bp.route("/verification/<int:verification_id>/download")
@role_required(roles.PROFESSIONAL)
def download_verification(verification_id):
    professional = _current_professional()
    doc = Verification.query.filter_by(
        id=verification_id, professional_profile_id=professional.id
    ).first_or_404()

    directory = current_app.config["VERIFICATION_UPLOAD_FOLDER"]
    # filename is stored as "<user_id>/<random-name>.<ext>"; send_from_directory
    # safely resolves this within `directory` and 404s on any traversal attempt.
    try:
        return send_from_directory(directory, doc.filename)
    except FileNotFoundError:
        abort(404)
