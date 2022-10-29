from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, BooleanField, PasswordField, TextAreaField, FileField, SelectField
from wtforms.validators import DataRequired, Email, Length, EqualTo


class Log_in_form(FlaskForm):
    email = StringField('Email: ')
    psw = PasswordField('Password: ', validators=[DataRequired(), Length(min=6, max=25, message='4 to 25')])
    remember = BooleanField('Remember', default=0)
    submit = SubmitField('Log in')

class Sign_up_form(FlaskForm):
    email = StringField('Email: ', validators=[Email()])
    psw = PasswordField('Password: ', validators=[DataRequired(), Length(min=6, max=25, message='4 to 25')])
    repsw = PasswordField('Rewrite password: ', validators=[DataRequired(), EqualTo('psw', message='These psw are not same')])
    submit = SubmitField('Sign up')

class Add_song(FlaskForm):
    title = StringField('Title', validators=[DataRequired()])
    band = StringField('Band', validators=[DataRequired()])
    submit = SubmitField('Add song')

class Add_group(FlaskForm):
    title = StringField('Title', validators=[DataRequired()])
    submit = SubmitField('Add group')

class Add_event(FlaskForm):
    title = StringField('Title', validators=[DataRequired()])
    tag = SelectField('Tag', choices=[('new_songs', 'New playlist'), ('new_group', 'New group')], validators=[DataRequired()])
    text = TextAreaField('Text', validators=[DataRequired()])
    photo = FileField('Photo')
    access_level = SelectField('Access')
    submit = SubmitField('Add group')