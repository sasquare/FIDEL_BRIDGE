from flask_wtf import FlaskForm
from wtforms import SelectField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, Optional

RATING_CHOICES = [
    ("5", "★★★★★ Excellent"),
    ("4", "★★★★☆ Good"),
    ("3", "★★★☆☆ Average"),
    ("2", "★★☆☆☆ Poor"),
    ("1", "★☆☆☆☆ Terrible"),
]


class ReviewForm(FlaskForm):
    rating = SelectField("Rating", choices=RATING_CHOICES, validators=[DataRequired()])
    comment = TextAreaField("Comment (optional)", validators=[Optional(), Length(max=1000)])
    submit = SubmitField("Submit Review")
