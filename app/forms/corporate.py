from flask_wtf import FlaskForm
from wtforms import DateField, IntegerField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, NumberRange, Optional

from app.models.corporate_request import TYPE_LABELS


class CorporateProfileForm(FlaskForm):
    company_name = StringField("Company Name", validators=[DataRequired(), Length(max=150)])
    rc_number = StringField("RC Number", validators=[Optional(), Length(max=50)])
    industry = StringField("Industry", validators=[Optional(), Length(max=120)])
    address = StringField("Office Address", validators=[Optional(), Length(max=255)])
    city = StringField("City", validators=[Optional(), Length(max=100)])
    state = StringField("State", validators=[Optional(), Length(max=100)])
    submit = SubmitField("Save Changes")


class CorporateRequestForm(FlaskForm):
    request_type = SelectField("Request Type", choices=list(TYPE_LABELS.items()), validators=[DataRequired()])
    title = StringField("Title", validators=[DataRequired(), Length(max=150)])
    description = TextAreaField("Details", validators=[DataRequired(), Length(max=2000)])
    location = StringField("Location", validators=[Optional(), Length(max=150)])
    budget_naira = IntegerField(
        "Estimated Budget (₦)", validators=[Optional(), NumberRange(min=0, message="Budget can't be negative.")]
    )
    preferred_date = DateField("Preferred Date", validators=[Optional()])
    submit = SubmitField("Submit Request")
