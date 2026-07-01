from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField, FileSize
from wtforms import IntegerField, SelectField, SelectMultipleField, StringField, SubmitField, TextAreaField, widgets
from wtforms.validators import DataRequired, Length, NumberRange, Optional

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
    submit = SubmitField("Save Changes")


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
