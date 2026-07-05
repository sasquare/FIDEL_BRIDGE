from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField, FileSize
from wtforms import StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, Optional


class CategoryForm(FlaskForm):
    name = StringField("Category Name", validators=[DataRequired(), Length(max=120)])
    icon_path = StringField(
        "Icon (SVG path data, optional)",
        validators=[Optional(), Length(max=2000)],
        render_kw={"placeholder": "e.g. M13 10V3L4 14h7v7l9-11h-7z"},
    )
    description = TextAreaField("Description", validators=[Optional(), Length(max=255)])
    image = FileField(
        "Photo (shown instead of the icon on the homepage)",
        validators=[
            Optional(),
            FileAllowed(["png", "jpg", "jpeg"], "Images only (PNG or JPG)."),
            FileSize(max_size=5 * 1024 * 1024, message="Image must be smaller than 5 MB."),
        ],
    )
    image_url = StringField(
        "Legacy image path (optional, advanced)",
        validators=[Optional(), Length(max=500)],
        render_kw={"placeholder": "/static/images/categories/electricians.jpg"},
        description=(
            "Only used if no photo is uploaded above. Must be a self-hosted file under "
            "app/static/images/ - external links (ibb.co, etc.) are blocked by the site's "
            "security policy and won't load."
        ),
    )
    submit = SubmitField("Save Category")
