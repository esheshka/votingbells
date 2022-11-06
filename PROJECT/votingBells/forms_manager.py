from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, BooleanField, PasswordField, TextAreaField, FileField, SelectField, validators
from wtforms.validators import DataRequired, Email, Length, EqualTo, re


class Log_in_form(FlaskForm):
    login = StringField('Логин: ')
    psw = PasswordField('Password: ', validators=[DataRequired(), Length(min=6, max=25, message='4 to 25')])
    remember = BooleanField('Remember', default=0)
    submit = SubmitField('Log in')

class Sign_up_form(FlaskForm):
    corp_email = StringField('Корпоративная почта:', validators=[Email()])
    login = StringField('Логин:')
    psw = PasswordField('Password:', validators=[DataRequired(), Length(min=6, max=25, message='4 to 25')])
    repsw = PasswordField('Rewrite password:', validators=[DataRequired(), EqualTo('psw', message='These psw are not same')])
    submit = SubmitField('Sign up')

class Add_song(FlaskForm):
    title = StringField('Title:', validators=[DataRequired()])
    band = StringField('Band:', validators=[DataRequired()])
    submit = SubmitField('Add song')

class Add_group(FlaskForm):
    title = StringField('Title:', validators=[DataRequired()])
    submit = SubmitField('Add group')

class Add_event(FlaskForm):
    title = StringField('Заголовок:', validators=[DataRequired()])
    tag = SelectField('Тег:', choices=[('new_songs', 'New playlist'), ('new_group', 'New group')], validators=[DataRequired()])
    text = TextAreaField('Текст:', validators=[DataRequired()])
    photo = FileField('Загрузите фото:')
    access_level = SelectField('Доступ:')
    submit = SubmitField('Опубликовать')