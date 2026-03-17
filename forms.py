from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, RadioField
from wtforms.validators import DataRequired, Email, Length

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit_customer = SubmitField('Log In as Customer')
    submit_producer = SubmitField('Log In as Producer')

class SignupForm(FlaskForm):
    full_name = StringField('Full Name', validators=[DataRequired(), Length(min=2, max=120)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    address = StringField('Address', validators=[DataRequired()])
    submit = SubmitField('Sign Up')

class DeliveryForm(FlaskForm):
    method = RadioField('Delivery Method',
                        choices=[('address', 'Deliver to your address'),
                                 ('pickup', 'Collect from a local pick up point')],
                        validators=[DataRequired()])
    submit = SubmitField('Next')

class PaymentForm(FlaskForm):
    card_number = StringField('Card Number', validators=[DataRequired()])
    expiry_date = StringField('Expiry Date', validators=[DataRequired()])
    cvc = StringField('CVC', validators=[DataRequired()])
    submit = SubmitField('Place Order')
