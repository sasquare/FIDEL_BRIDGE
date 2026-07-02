from flask_wtf import FlaskForm
from wtforms import BooleanField, PasswordField, SelectField, StringField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Optional, ValidationError

from app.models.user import User


class RegistrationForm(FlaskForm):
    full_name = StringField("Full Name", validators=[DataRequired(), Length(max=120)])
    email = StringField("Email Address", validators=[DataRequired(), Email(), Length(max=255)])
    phone = StringField("Phone Number", validators=[Optional(), Length(max=20)])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=8)])
    confirm_password = PasswordField(
        "Confirm Password", validators=[DataRequired(), EqualTo("password", message="Passwords must match.")]
    )

    def validate_email(self, field):
        if User.query.filter_by(email=field.data.strip().lower()).first():
            raise ValidationError("An account with this email already exists.")


class CustomerRegistrationForm(RegistrationForm):
    city = StringField("City", validators=[Optional(), Length(max=100)])
    submit = SubmitField("Create Customer Account")


class ProfessionalRegistrationForm(RegistrationForm):
    profession = StringField("Profession / Trade", validators=[DataRequired(), Length(max=120)])
    category_id = SelectField("Category", coerce=int, validators=[DataRequired(message="Please choose a category.")])
    city = StringField("City", validators=[Optional(), Length(max=100)])
    submit = SubmitField("Create Professional Account")


class CorporateRegistrationForm(RegistrationForm):
    company_name = StringField("Company Name", validators=[DataRequired(), Length(max=150)])
    rc_number = StringField("RC Number", validators=[Optional(), Length(max=50)])
    industry = StringField("Industry", validators=[Optional(), Length(max=120)])
    submit = SubmitField("Create Corporate Account")


class LoginForm(FlaskForm):
    email = StringField("Email Address", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    remember_me = BooleanField("Remember Me")
    submit = SubmitField("Log In")


class ForgotPasswordForm(FlaskForm):
    email = StringField("Email Address", validators=[DataRequired(), Email()])
    submit = SubmitField("Send Reset Link")


class ResetPasswordForm(FlaskForm):
    password = PasswordField("New Password", validators=[DataRequired(), Length(min=8)])
    confirm_password = PasswordField(
        "Confirm New Password", validators=[DataRequired(), EqualTo("password", message="Passwords must match.")]
    )
    submit = SubmitField("Reset Password")
