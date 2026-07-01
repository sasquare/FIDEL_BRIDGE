from flask_wtf import FlaskForm
from wtforms import DateField, IntegerField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, NumberRange, Optional


class BookingForm(FlaskForm):
    title = StringField("Job Title", validators=[DataRequired(), Length(max=150)])
    description = TextAreaField("Describe what you need", validators=[DataRequired(), Length(max=2000)])
    location = StringField("Location", validators=[Optional(), Length(max=150)])
    budget_naira = IntegerField(
        "Your Budget (₦)", validators=[Optional(), NumberRange(min=0, message="Budget can't be negative.")]
    )
    preferred_date = DateField("Preferred Date", validators=[Optional()])
    submit = SubmitField("Send Request")
