from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField, FileSize
from wtforms import (
    BooleanField,
    IntegerField,
    SelectField,
    SelectMultipleField,
    StringField,
    SubmitField,
    TextAreaField,
    widgets,
)
from wtforms.validators import DataRequired, Length, NumberRange, Optional

from app.models.professional import (
    PRICING_TYPE_LABELS,
    PRICING_TYPES,
    PROFESSIONAL_TYPE_INDIVIDUAL,
    PROFESSIONAL_TYPE_REGISTERED_BUSINESS,
)

PROFESSIONAL_TYPE_CHOICES = [
    (PROFESSIONAL_TYPE_INDIVIDUAL, "Individual Professional"),
    (PROFESSIONAL_TYPE_REGISTERED_BUSINESS, "Registered Business"),
]

PRICING_TYPE_CHOICES = [(value, PRICING_TYPE_LABELS[value]) for value in PRICING_TYPES]

WEEKDAY_CHOICES = [
    ("Mon", "Monday"),
    ("Tue", "Tuesday"),
    ("Wed", "Wednesday"),
    ("Thu", "Thursday"),
    ("Fri", "Friday"),
    ("Sat", "Saturday"),
    ("Sun", "Sunday"),
]

DOCUMENT_TYPE_CHOICES = [
    ("Government ID", "Government-Issued ID"),
    ("Proof of Address", "Proof of Address"),
    ("Certification", "Certification / License"),
    ("Other", "Other"),
]


class MultiCheckboxField(SelectMultipleField):
    widget = widgets.ListWidget(prefix_label=False)
    option_widget = widgets.CheckboxInput()


class ProfessionalProfileForm(FlaskForm):
    profession = StringField("Profession / Trade", validators=[DataRequired(), Length(max=120)])
    category_id = SelectField("Category", coerce=int, validators=[DataRequired(message="Please choose a category.")])
    city = StringField("City", validators=[Optional(), Length(max=100)])
    state = StringField("State", validators=[Optional(), Length(max=100)])
    years_experience = IntegerField("Years of Experience", validators=[Optional(), NumberRange(min=0, max=80)])
    bio = TextAreaField("Bio", validators=[Optional(), Length(max=2000)])
    available_days = MultiCheckboxField("Available Days", choices=WEEKDAY_CHOICES, validators=[Optional()])
    available_hours = StringField(
        "Typical Hours", validators=[Optional(), Length(max=100)], render_kw={"placeholder": "e.g. 8:00 AM - 6:00 PM"}
    )
    profile_photo = FileField(
        "Profile Photo",
        validators=[
            Optional(),
            FileAllowed(["png", "jpg", "jpeg"], "Images only (PNG or JPG)."),
            FileSize(max_size=5 * 1024 * 1024, message="Image must be smaller than 5 MB."),
        ],
    )
    professional_type = SelectField(
        "Business Type", choices=PROFESSIONAL_TYPE_CHOICES, validators=[DataRequired()]
    )
    # business_name/business_registration_number are only required when
    # professional_type is "registered_business" - that depends on another
    # field's value, so it's enforced in the route rather than here.
    business_name = StringField("Business Name", validators=[Optional(), Length(max=150)])
    business_registration_number = StringField(
        "CAC Registration Number", validators=[Optional(), Length(max=50)]
    )
    submit = SubmitField("Save Changes")


class PricingForm(FlaskForm):
    pricing_type = SelectField("Pricing Model", choices=PRICING_TYPE_CHOICES, validators=[DataRequired()])
    # Required only when pricing_type isn't "not_specified" - enforced in the
    # route, same pattern as ProfessionalProfileForm's business fields.
    pricing_amount = IntegerField(
        "Amount (₦)", validators=[Optional(), NumberRange(min=0, message="Amount can't be negative.")]
    )
    requires_inspection = BooleanField("Requires an on-site inspection before final pricing")
    consultation_fee = IntegerField(
        "Consultation Fee (₦)",
        validators=[Optional(), NumberRange(min=0, message="Fee can't be negative.")],
        render_kw={"placeholder": "Leave blank if you don't charge for consultations"},
    )
    submit = SubmitField("Save Pricing")


class SkillForm(FlaskForm):
    name = StringField("Skill", validators=[DataRequired(), Length(max=80)], render_kw={"placeholder": "e.g. Solar Installation"})
    submit = SubmitField("Add Skill")


class PortfolioItemForm(FlaskForm):
    title = StringField("Title", validators=[DataRequired(), Length(max=150)])
    description = TextAreaField("Description", validators=[Optional(), Length(max=1000)])
    image = FileField(
        "Photo",
        validators=[
            Optional(),
            FileAllowed(["png", "jpg", "jpeg"], "Images only (PNG or JPG)."),
            FileSize(max_size=5 * 1024 * 1024, message="Image must be smaller than 5 MB."),
        ],
    )
    submit = SubmitField("Add to Portfolio")


class VerificationUploadForm(FlaskForm):
    document_type = SelectField("Document Type", choices=DOCUMENT_TYPE_CHOICES, validators=[DataRequired()])
    file = FileField(
        "Document",
        validators=[
            DataRequired(message="Please choose a file to upload."),
            FileAllowed(["png", "jpg", "jpeg", "pdf"], "Images or PDF only."),
            FileSize(max_size=5 * 1024 * 1024, message="File must be smaller than 5 MB."),
        ],
    )
    submit = SubmitField("Upload Document")
