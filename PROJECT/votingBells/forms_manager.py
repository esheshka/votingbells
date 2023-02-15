from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, BooleanField, PasswordField, TextAreaField, FileField, SelectField, validators
from wtforms.validators import DataRequired, Email, Length, EqualTo, re


class Log_in_form(FlaskForm):
    login = StringField('Логин')
    psw = PasswordField('Пароль', validators=[DataRequired()])
    remember = BooleanField('Запомнить меня', default=0)
    submit = SubmitField('Войти')

class Sign_up_form(FlaskForm):
    corp_email = StringField('Корпоративная почта')
    login = StringField('Логин')
    psw = PasswordField('Пароль', validators=[DataRequired()])
    repsw = PasswordField('Повтор пароля', validators=[DataRequired()])
    submit = SubmitField('Зарегистрироваться')

class Sec_email_form(FlaskForm):
    email = StringField('Почта')
    submit = SubmitField('Отправить письмо')


class Add_song(FlaskForm):
    title = StringField('Название', validators=[DataRequired()])
    band = StringField('Группа', validators=[DataRequired()])
    submit = SubmitField('Добавить')

class Add_group(FlaskForm):
    title = StringField('Название', validators=[DataRequired()])
    submit = SubmitField('Добавить')

class Add_event(FlaskForm):
    title = StringField('Название')
    tag = SelectField('Тег', choices=[('other', 'Другое'), ('new_group', 'Новая тема'), ('new_songs', 'Новый плейлист')], validators=[DataRequired()])
    text = TextAreaField('Текст', validators=[DataRequired()])
    photo = FileField('Загрузите фото')
    access_level = SelectField('Доступ')
    submit = SubmitField('Опубликовать')


class Add_notification(FlaskForm):
    text = TextAreaField('Текст', validators=[DataRequired()])
    access_level = SelectField('Доступ')
    submit = SubmitField('Опубликовать')

class Upload_bell(FlaskForm):
    bell = FileField('Загрузите звонок')
    submit = SubmitField('Загрузить')