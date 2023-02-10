from flask import render_template, url_for, redirect, make_response, send_file
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import datetime
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_socketio import SocketIO, emit
import smtplib
from email.mime.text import MIMEText
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadTimeSignature
from io import BytesIO
import eventlet

import os


# Мои скрипты
# Скрипт WTForms определяющий forms, упрощающий с ними работу
from forms_manager import Log_in_form, Sign_up_form, Sec_email_form, Add_song, Add_group, Add_event, Add_notification, Upload_bell
# Скрипт, для получения данных о пользователе
from login_user import User_login


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SECRET_KEY'] = 'asdfghhgfdsaadfhfhgdjrebcvndffh'
app.config['JWT_ALGORITHM'] = 'HS256'
db = SQLAlchemy(app)

socketio = SocketIO(app, async_mode='eventlet')

# Данные для отправки писем
sender = 'lyceumbells@gmail.com'
password = 'ffcginsdzvekrcog'

# Управление токенами
s = URLSafeTimedSerializer(app.config['SECRET_KEY'])


class Users(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(50), default=None)
    corp_email = db.Column(db.String(50), unique=True)
    login = db.Column(db.String(50), unique=True)
    psw = db.Column(db.String(500), nullable=True)
    bells = db.Column(db.Integer, default=10)
    position = db.Column(db.String, default='user')
    confirmed = db.Column(db.Boolean, nullable=False, default=False)
    grade = db.Column(db.Integer)

class Corp_Users(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(50), unique=True)
    firstname = db.Column(db.String(50))
    secondname = db.Column(db.String(50))
    thirdname = db.Column(db.String(50))
    grade = db.Column(db.Integer)

class Songs(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=True)
    band = db.Column(db.String(100), nullable=True)
    bell = db.Column(db.LargeBinary, default=None)
    name = db.Column(db.Integer, default=None)
    offered_group = db.Column(db.Integer)
    is_new = db.Column(db.Integer, default=1)
    approved = db.Column(db.Integer, default=0)
    likes = db.Column(db.Integer, default=0)
    recent_likes = db.Column(db.Integer, default=0)

class Groups(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), unique=True)
    avatar = db.Column(db.LargeBinary, default=None)
    is_new = db.Column(db.Integer, default=1)
    approved = db.Column(db.Integer, default=0)
    likes = db.Column(db.Integer, default=0)
    recent_likes = db.Column(db.Integer, default=0)

class Users_choices_songs(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    song_id = db.Column(db.Integer)
    choice = db.Column(db.Integer)

class Users_choices_groups(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    group_id = db.Column(db.Integer)
    choice = db.Column(db.Integer)

class Groups_Songs(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('groups.id'))
    song_id = db.Column(db.Integer, db.ForeignKey('songs.id'))

class Events(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    title = db.Column(db.String(50))
    cs = db.Column(db.Integer, default=None)
    tag = db.Column(db.String(500))
    photo = db.Column(db.LargeBinary, default=None)
    text = db.Column(db.String(500))
    access_level = db.Column(db.String(50))
    time = db.Column(db.DateTime, default=datetime.datetime.now())

class Notifications(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    title = db.Column(db.String(50))
    text = db.Column(db.String(500))
    access_level = db.Column(db.String(50))
    time = db.Column(db.DateTime, default=datetime.datetime.now())

class Choosen_Songs(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    num = db.Column(db.Integer)
    song_id = db.Column(db.Integer, db.ForeignKey('songs.id'))

def create_db():
    global db
    global app
    with app.app_context():
        db.create_all()


login_manager = LoginManager(app)
login_manager.login_view = '/log_in'

# Переменная отвечающая за что сейчас идет голосование
voting_songs_or_groups = 'groups'


# список ролей и уровень их доступа
access_accordance = (
    {'name': 'user', 'group': 'all'},
    {'name': 'designer', 'group': 'design'},
    {'name': 'placer', 'group': 'tech'},
    {'name': 'cutter', 'group': 'tech'},
    {'name': 'text_writer', 'group': 'design'},
    {'name': 'supporter', 'group': 'tech'},
    {'name': 'coordinator_design', 'group': 'design'},
    {'name': 'coordinator_tech', 'group': 'tech'},
    {'name': 'admin', 'group': 'admin'},
    {'name': 'chief', 'group': 'admin'})

position_groups = {
    'user': 'all',
    'designer': 'design',
    'placer': 'tech',
    'cutter': 'tech',
    'text_writer': 'design',
    'supporter': 'tech',
    'coordinator_design': 'design',
    'coordinator_tech': 'tech',
    'admin': 'admin',
    'chief': 'admin'}


# id выбранной на прошлом голосовании темы
selected_group = 1


# Определяем пользователя
@login_manager.user_loader
def load_user(user_id):
    print('load_user ' + user_id)
    return User_login().fromDB(Users.query.filter_by(id=user_id).first())

# Главная страница, перебрасывающая нас на проходяещее голосование
@app.route('/')
@app.route('/voting')
@login_required
def voting():
    if voting_songs_or_groups == 'songs':
        return redirect(url_for('voting_songs'))
    else:
        return redirect(url_for('voting_groups'))


# # Страница голосования за песни
@app.route('/voting_songs')
@login_required
def voting_songs():
    if voting_songs_or_groups == 'groups':
        return redirect(url_for('voting'))

    # Выбираем песни удовлетворяющие голосованию
    songs = []
    for song in Songs.query.order_by(Songs.recent_likes.desc()).all():
        if Groups_Songs.query.filter_by(song_id=song.id).filter_by(group_id=selected_group).count() > 0 or song.approved == 0:
            songs.append(song)

    # Все голоса пользователя
    user_likes = Users_choices_songs.query.filter_by(user_id=current_user.get_id())

    # Песни за которые голосовал пользователь
    id_songs = db.session.query(Users_choices_songs.song_id).filter_by(user_id=current_user.get_id()).all()
    ids = []
    for m in id_songs:
        ids.append(str(m)[1:-2])
    user_selected_songs = Songs.query.filter(Songs.id.in_(ids)).order_by(Songs.recent_likes.desc()).all()

    return render_template('voting_songs.html', selected_group=Groups.query.filter_by(id=selected_group).first().title,
                           voting_songs_or_groups=voting_songs_or_groups, songs=songs,
                           user_likes=user_likes, user_selected_songs=user_selected_songs)


# Страница голосования за тему
@app.route('/voting_groups')
@login_required
def voting_groups():
    groups = Groups.query.order_by(Groups.recent_likes.desc()).all()

    # Все голоса пользователя
    user_likes = Users_choices_groups.query.filter_by(user_id=current_user.get_id())

    # Темы за которые голосовал пользователь
    id_groups = db.session.query(Users_choices_groups.group_id).filter_by(user_id=current_user.get_id()).all()
    ids = []
    for m in id_groups:
        ids.append(str(m)[1:-2])
    user_selected_groups = Groups.query.filter(Groups.id.in_(ids)).order_by(Groups.recent_likes.desc()).all()

    return render_template('voting_groups.html',  voting_songs_or_groups=voting_songs_or_groups, groups=groups,
                           user_likes=user_likes, user_selected_groups=user_selected_groups)


# Завершаем голосование и переходим к следующему
# Функция доступна только админам
# Возвращает все временные переменные к изначальным значениям
@app.route('/change_voting')
@login_required
def change_voting():
    global selected_group
    global voting_songs_or_groups

    if current_user.get_position() == 'chief' or current_user.get_position() == 'admin':
        if voting_songs_or_groups == 'songs':
            voting_songs_or_groups = 'groups'

            # Сброс временных значений
            Users_choices_groups.query.delete()
            db.session.execute('UPDATE users SET bells=10')
            db.session.execute('UPDATE groups SET recent_likes=0')
            db.session.commit()

            # Добавление еще не добавленных песен в тему
            songs = []
            for song in Songs.query.order_by(Songs.recent_likes.desc()).all():
                if song.is_new == 1:
                    song.approved = 1
                    song.is_new = 0
                    gs = Groups_Songs(song_id=song.id, group_id=selected_group)
                    db.session.add(gs)

                if Groups_Songs.query.filter_by(song_id=song.id).filter_by(
                        group_id=selected_group).count() > 0 or song.approved == 0:
                    songs.append(song)
                    if len(songs) == 20:
                        break

            # Создание шаблона под Событие с новым плейлистом
            cs = db.session.query(Choosen_Songs).order_by(Choosen_Songs.num.desc()).first()
            if cs==None:
                num = 0
            else:
                num = cs.num + 1
            for song in songs:
                cs = Choosen_Songs(song_id=song.id, num=num)
                db.session.add(cs)
            db.session.flush()
            db.session.commit()

            # Создание Уведомления о новом плейлисте
            songs = []
            for song in Songs.query.order_by(Songs.recent_likes.desc()).all():
                if Groups_Songs.query.filter_by(song_id=song.id).filter_by(
                        group_id=selected_group).count() > 0 or song.approved == 0:
                    songs.append(song)
            text = f'Новый плейлист по теме {Groups.query.filter_by(id=selected_group).first().title}!'
            i = 1
            for song in songs[:20]:
                text += '\n' + f'{i}) {song.title}'
                i += 1
            print(text)
            note = Notifications(user_id=current_user.get_id(), title='Новый плейлист', text=text, access_level='all')
            db.session.add(note)
            db.session.flush()
            db.session.commit()

            return redirect(url_for('voting_groups'))
        elif voting_songs_or_groups == 'groups':
            selected_group = Groups.query.order_by(Groups.recent_likes.desc()).first().id
            voting_songs_or_groups = 'songs'

            # Сброс временных значений
            Users_choices_songs.query.delete()
            Songs.query.filter_by(approved=0).delete()
            db.session.execute('UPDATE songs SET offered_group="None"')
            db.session.execute('UPDATE users SET bells=10')
            db.session.execute('UPDATE songs SET recent_likes=0')

            # Создание Уведомления о новой теме
            text = f'Новая тема - {Groups.query.filter_by(id=selected_group).first().title}!'
            print(text)
            note = Notifications(user_id=current_user.get_id(), title='Новая тема', text=text, access_level='all')
            db.session.add(note)
            db.session.flush()
            db.session.commit()

            return redirect(url_for('voting_songs'))

    return redirect(url_for('voting'))


# JS функция отвечающая за выставление пользователем оценки песни
@socketio.on('likes songs')
def likes_songs(data):
    # Проверка голосовал ли пользователь за эту песню раньше
    another_choice = Users_choices_songs.query.filter_by(user_id=current_user.get_id()).filter_by(song_id=data[0])
    if another_choice.count() > 0:
        choice = another_choice.first()
        user = Users.query.filter_by(id=current_user.get_id()).first()

        if choice.choice*int(data[1]) >= 0:
            if current_user.get_bells() == 0:
                return 0
        else:
            user.bells = user.bells + 2

        # Изменение всех переменных завязанных на выбор
        user.bells = user.bells - 1
        choice.choice = int(choice.choice) + int(data[1])
        song = Songs.query.filter_by(id=data[0]).first()
        song.likes += int(data[1])
        song.recent_likes += int(data[1])

        db.session.flush()
        db.session.commit()
    else:
        if current_user.get_bells() == 0:
            return 0
        choice = Users_choices_songs(user_id=current_user.get_id(), song_id=int(data[0]), choice=int(data[1]))
        user = Users.query.filter_by(id=current_user.get_id()).first()
        song = Songs.query.filter_by(id=data[0]).first()
        db.session.add(choice)
        song.likes += int(data[1])
        song.recent_likes += int(data[1])
        user.bells = user.bells - 1
        db.session.flush()
        db.session.commit()

    # Вычисление данных для отправки пользователям
    count = Songs.query.filter_by(id=data[0]).first().recent_likes
    user_like = Users_choices_songs.query.filter_by(user_id=current_user.get_id()).filter_by(song_id=data[0]).first()
    if user_like == None:
        user_like = 0
    else:
        user_like = user_like.choice

    # JS Отправка данных
    emit('show my likes song', [data[0], user_like])
    emit("vote totals songs", [count, data[0]], broadcast=True)
    emit('show bells', data=1, broadcast=True)


# JS функция отвечающая за выставление пользователем оценки теме
@socketio.on('likes groups')
def likes_groups(data):
    # Проверка голосовал ли пользователь за эту тему раньше
    another_choice = Users_choices_groups.query.filter_by(user_id=current_user.get_id()).filter_by(group_id=data[0])
    if another_choice.count() > 0:
        choice = another_choice.first()
        user = Users.query.filter_by(id=current_user.get_id()).first()

        if choice.choice * int(data[1]) >= 0:
            if current_user.get_bells() == 0:
                return 0
        else:
            user.bells = user.bells + 2

        # Изменение всех переменных завязанных на выбор
        user.bells = user.bells - 1
        choice.choice = int(choice.choice) + int(data[1])
        group = Groups.query.filter_by(id=data[0]).first()
        group.likes += int(data[1])
        group.recent_likes += int(data[1])

        db.session.flush()
        db.session.commit()
    else:
        if current_user.get_bells() == 0:
            return 0
        choice = Users_choices_groups(user_id=current_user.get_id(), group_id=int(data[0]), choice=int(data[1]))
        user = Users.query.filter_by(id=current_user.get_id()).first()
        user.bells = user.bells - 1
        db.session.add(choice)
        group = Groups.query.filter_by(id=data[0]).first()
        group.likes += int(data[1])
        group.recent_likes += int(data[1])

        db.session.flush()
        db.session.commit()

    # Вычисление данных для отправки пользователям
    count = Groups.query.filter_by(id=data[0]).first().recent_likes
    user_like = Users_choices_groups.query.filter_by(user_id=current_user.get_id()).filter_by(group_id=data[0]).first()
    if user_like == None:
        user_like = 0
    else:
        user_like = user_like.choice

    # JS Отправка данных
    emit('show my likes group', [data[0], user_like])
    emit("vote totals groups", [count, data[0]], broadcast=True)
    emit('show bells', data=1, broadcast=True)

# Страница добавления песни
# Обрабатываем попытку добавить песню
@app.route('/add_song', methods=('POST', 'GET'))
@login_required
def add_song():
    if voting_songs_or_groups == 'groups':
        return redirect(url_for('add_group'))

    # Обработка формы
    form = Add_song()
    if form.validate_on_submit():
        # Проверка находится ли эта песня в БД вообще
        song = Songs.query.filter_by(title=form.title.data).filter_by(band=form.band.data)
        if song.count() > 0:
            if Groups_Songs.query.filter_by(song_id=song.first().id).filter_by(group_id=selected_group).count() > 0:
                return render_template('add_song.html', voting_songs_or_groups=voting_songs_or_groups, form=form,
                                       titles=db.session.query(Songs.title).filter(Songs.approved == 1).all(),
                                       bands=db.session.query(Songs.band).all(), error='Эта песня уже находится в теме')
            else:
                song.first().offered_group = selected_group
                song.first().approved = 0

                db.session.flush()
                db.session.commit()

                return redirect(url_for('voting'))
        else:
            new_song = Songs(title=form.title.data, band=form.band.data)
            db.session.add(new_song)

            db.session.flush()
            db.session.commit()

            return redirect(url_for('voting'))

    return render_template('add_song.html', voting_songs_or_groups=voting_songs_or_groups, form=form,
                           titles=db.session.query(Songs.title).filter(Songs.approved == 1).all(),
                           bands=db.session.query(Songs.band).all())


# Страница добавления темы
# Обрабатываем попытку добавить тему
@app.route('/add_group', methods=('POST', 'GET'))
@login_required
def add_group():
    if voting_songs_or_groups == 'songs':
        return redirect(url_for('add_song'))

    # Обработка формы
    form = Add_group()
    if form.validate_on_submit():
        # Проверка находится ли эта тема в БД вообще
        group = Groups.query.filter_by(title=form.title.data)
        if group.count() > 0:
            return render_template('add_group.html', voting_songs_or_groups=voting_songs_or_groups, form=form,
                                   titles=db.session.query(Groups.title).filter(Groups.approved == 1).all(),
                                   error='Эта тема уже добавленна')
        else:
            new_group = Groups(title=form.title.data)
            db.session.add(new_group)

            db.session.flush()
            db.session.commit()

            return redirect(url_for('voting'))

    return render_template('add_group.html', voting_songs_or_groups=voting_songs_or_groups, form=form,
                           titles=db.session.query(Groups.title).filter(Groups.approved == 1).all())


# Отправляем список всех предложенных песен
# Функция доступна только админам
@app.route('/approve_songs')
@login_required
def approve_songs():
    if current_user.get_position() in ['chief', 'admin']:
        return render_template('approve_songs.html', voting_songs_or_groups=voting_songs_or_groups,
                               songs=Songs.query.filter_by(approved=0).order_by(Songs.likes.desc()).all(),
                               titles=db.session.query(Songs.title).filter(Songs.approved == 1).all(),
                               bands=db.session.query(Songs.band).all())
    else:
        return redirect(url_for('voting'))


# Отправляем список всех предложенных тем
# Функция доступна только админам
@app.route('/approve_groups')
@login_required
def approve_groups():
    if current_user.get_position() in ['chief', 'admin']:
        return render_template('approve_groups.html', voting_songs_or_groups=voting_songs_or_groups,
                               groups=Groups.query.filter_by(approved=0).order_by(Groups.likes.desc()).all(),
                               titles=db.session.query(Groups.title).filter(Groups.approved == 1).all())
    else:
        return redirect(url_for('voting'))


# JS функция подтверждения добавления песни
# data <=> [id, choice]
@socketio.on('approve song')
def approve_song(data):
    song = Songs.query.filter_by(id=data[0]).first()
    approved = 0
    song.approved = 1
    if data[1] == 'Yes':
        approved = 1
        song.is_new = 0
        gs = Groups_Songs(song_id=data[0], group_id=selected_group)
        db.session.add(gs)
    elif Groups_Songs.query.filter_by(song_id=data[0]).count() == 0:
        return_bells_by_song(data[0])
        song.recent_bells = 0
        db.session.delete(song)

    db.session.flush()
    db.session.commit()

    # JS Отправка данных
    emit("is approve song", [data[0], approved], broadcast=True)
    emit('show bells', data=1, broadcast=True)


# JS функция подтверждения добавления темы
# data <=> [id, choice]
@socketio.on('approve group')
def approve_group(data):
    group = Groups.query.filter_by(id=data[0]).first()
    approved = 1
    group.approved = 1
    group.is_new = 0
    if data[1] == 'No':
        approved = 0
        return_bells_by_group(data[0])
        group.recent_bells = 0
        db.session.delete(group)

    db.session.flush()
    db.session.commit()

    # JS Отправка данных
    emit("is approve group", [data[0], approved], broadcast=True)
    emit('show bells', data=1, broadcast=True)


# JS функция возвращает колличество bell-ов
@socketio.on('get bells')
def get_bells():
    emit('show bells self', current_user.get_bells())


# Страница песни по id
@app.route('/song/<id>', methods=['GET', 'POST'])
@login_required
def song(id):
    if Songs.query.filter_by(id=id).count() == 0:
        return redirect(url_for('voting'))

    # Все темы этой песни
    groups = []
    for group in Groups_Songs.query.filter_by(song_id=id).all():
        groups.append(Groups.query.filter_by(id=group.group_id).first().title)

    # Обработка формы добавления трека
    form = Upload_bell()
    if form.validate_on_submit():
        try:
            song = Songs.query.filter_by(id=id).first()
            if form.bell.data:
                bell = form.bell.data
                name = int(str(bell.filename)[:-4])
                print(name)
                if name == None:
                    return render_template('song.html', song=Songs.query.filter_by(id=id).first(), groups=groups,
                                           voting_songs_or_groups=voting_songs_or_groups, form=form,
                                           error='Неправильное название трека')

                bell = bell.read()
                song.bell = None
                song.bell = bell
                song.name = name

                db.session.flush()
                db.session.commit()
        except:
            db.session.rollback()

            return render_template('song.html', song=Songs.query.filter_by(id=id).first(), groups=groups,
                                   voting_songs_or_groups=voting_songs_or_groups, form=form, error='Трек не был добавлен')

    return render_template('song.html', song=Songs.query.filter_by(id=id).first(), groups=groups,
                           voting_songs_or_groups=voting_songs_or_groups, form=form)


# Страница темы по id
@app.route('/group/<id>')
@login_required
def group(id):
    if Groups.query.filter_by(id=id).count() == 0:
        return redirect(url_for('voting'))

    # Все песни этой темы
    songs = []
    for song in Groups_Songs.query.filter_by(group_id=id).all():
        songs.append(Songs.query.filter_by(id=song.song_id).first())

    return render_template('group.html', group=Groups.query.filter_by(id=id).first(), songs=songs, voting_songs_or_groups=voting_songs_or_groups)


# Вспомогательная функция, возвращающая bell-ы пользователям при не подтверждении песни за которую они голосовали
def return_bells_by_song(id):
    for choice in Users_choices_songs.query.filter_by(song_id=id):
        Users.query.filter_by(id=choice.user_id).first().bells += abs(choice.choice)
        db.session.delete(choice)
    db.session.flush()
    db.session.commit()

# Вспомогательная функция, возвращающая bell-ы пользователям при не подтверждении темы за которую они голосовали
def return_bells_by_group(id):
    for choice in Users_choices_groups.query.filter_by(group_id=id):
        print('reterns ' + str(abs(choice.choice)) + ' bells to ' + str(Users.query.filter_by(id=choice.user_id).first().id))
        Users.query.filter_by(id=choice.user_id).first().bells += abs(choice.choice)
        db.session.delete(choice)
    db.session.flush()
    db.session.commit()


# Регистрация
@app.route("/sign_up", methods=("POST", "GET"))
def sign_up():
    # Обработка формы
    form = Sign_up_form()
    if form.validate_on_submit():
        # Нахождение пользователя в списке учащихся
        corp_user = Corp_Users.query.filter_by(email=form.corp_email.data)
        if corp_user.count() == 0:
            return render_template('sign_up.html', voting_songs_or_groups=voting_songs_or_groups, form=form, error='Ученик не найден')
        else:
            try:
                # Создание\изменение учетки пользователя
                user = Users.query.filter_by(confirmed=0).filter_by(corp_email=corp_user.first().email)

                hash = generate_password_hash(form.psw.data)
                if user.count() > 0:
                    user = user.first()
                    user.login = form.login.data
                    user.psw = hash
                else:
                    user = Users(login=form.login.data, psw=hash, grade=corp_user.first().grade, corp_email=corp_user.first().email)
                    db.session.add(user)

                db.session.flush()
                db.session.commit()
            except:
                db.session.rollback()
                print("Ошибка добавления в БД")
                return render_template('sign_up.html', voting_songs_or_groups=voting_songs_or_groups, form=form, error='Пользователь с такой почтой уже зарегистрирован')

            # Создание письма подтверждения почты
            token = s.dumps(form.corp_email.data, salt='email-confirm')
            link = url_for('confirm_corp_email', token=token, external=True)
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(sender, password)
            # msg = MIMEText('Confirm link: https://flask-test-esheshka.herokuapp.com/' + link)
            msg = MIMEText('Confirm link: http://127.0.0.1:5000' + link)
            msg['Subject'] = 'Confirm email'
            server.sendmail(sender, form.corp_email.data, str(msg))

            return redirect(url_for('log_in'))

    return render_template('sign_up.html', voting_songs_or_groups=voting_songs_or_groups, form=form)


# Страница подключения второй почты
@app.route("/sec_email", methods=("POST", "GET"))
def sec_email():
    # Обработка формы
    form = Sec_email_form()
    if form.validate_on_submit():
        user = Users.query.filter_by(id=current_user.get_id())

        # Создание письма подтверждения почты
        token = s.dumps(form.email.data, salt='email-confirm')
        link = url_for('confirm_email', token=token, external=True)
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender, password)
        # msg = MIMEText('Confirm link: https://flask-test-esheshka.herokuapp.com' + link)
        msg = MIMEText('Confirm link: http://127.0.0.1:5000' + link)
        msg['Subject'] = 'Confirm email'
        server.sendmail(sender, form.email.data, str(msg))
        print(f'Письмо отправленно на {form.email.data}')

        return redirect(url_for('profile'))

    return render_template('sec_email.html', voting_songs_or_groups=voting_songs_or_groups, form=form)


# Обработка подтверждения почты
@app.route('/confirm_email/<token>')
def confirm_email(token):
    try:
        email = s.loads(token, salt='email-confirm', max_age=60)
    except SignatureExpired:
        return 'The token is expired'
    user = Users.query.filter_by(id=current_user.get_id()).first()
    user.email = email

    db.session.flush()
    db.session.commit()

    return redirect(url_for('profile'))


# Обработка подтверждения корпоративной почты
@app.route('/confirm_corp_email/<token>')
def confirm_corp_email(token):
    try:
        email = s.loads(token, salt='email-confirm', max_age=60)
    except SignatureExpired:
        return 'The token is expired'
    user = Users.query.filter_by(corp_email=email).first()
    user.confirmed = True

    db.session.flush()
    db.session.commit()

    return redirect(url_for('log_in'))


# Вход
@app.route('/log_in', methods=('POST', 'GET'))
def log_in():
    if current_user.is_authenticated:
        return redirect(url_for('profile'))

    # Обработка формы
    form = Log_in_form()
    if form.validate_on_submit():
        if Users.query.filter_by(login=form.login.data).count() > 0 and\
                check_password_hash(Users.query.filter_by(login=form.login.data).first().psw, form.psw.data):
            if Users.query.filter_by(login=form.login.data).first().confirmed == 0:
                return render_template('log_in.html', voting_songs_or_groups=voting_songs_or_groups, form=form, error='Подтвердите свою копоративную почту')

            user_login = User_login().create(Users.query.filter_by(login=form.login.data).first())
            login_user(user_login, remember=form.remember.data)

            return redirect(url_for('profile'))
        else:
            return render_template('log_in.html', voting_songs_or_groups=voting_songs_or_groups, form=form, error='Неверный логин или пароль')

    return render_template('log_in.html', voting_songs_or_groups=voting_songs_or_groups, form=form)


# Выход
@app.route('/log_out', methods=('POST', 'GET'))
@login_required
def log_out():
    logout_user()
    return redirect(url_for('log_in'))


# Страница профиля
@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html', voting_songs_or_groups=voting_songs_or_groups,
                           user=Users.query.filter_by(id=current_user.get_id()).first())


# Страница событий
@app.route('/events')
@login_required
def events():
    # Список доступных Событий
    if current_user.get_position() not in ['chief', 'admin']:
        events = Events.query.filter((Events.access_level == 'all') | (Events.access_level == position_groups.get(current_user.get_position())))
    else:
        events = Events.query
    events = events.order_by(Events.time.desc()).all()
    return render_template('events.html', voting_songs_or_groups=voting_songs_or_groups, events=events)


# Страница добавления события
@app.route('/add_event', methods=['GET', 'POST'])
@login_required
def add_event():
    if current_user.get_position() == 'user':
        return redirect(url_for('events'))

    # Обработка формы
    form = Add_event()
    if current_user.get_position() in ['chief', 'admin']:
        form.access_level.choices = [('local', 'Админы'), ('all', 'Все'), ('design', 'Дизайнеры'), ('tech', 'Техники')]
    else:
        form.access_level.choices = [('local', 'Отдел'), ('all', 'Все')]

    if form.validate_on_submit():
        access_level = form.access_level.data
        if form.access_level.data == 'local':
            access_level = position_groups.get(current_user.get_position())

        new_event = Events(title=form.title.data, tag=form.tag.data, text=form.text.data, access_level=access_level, user_id=current_user.get_id())

        if form.photo.data:
            new_event.photo = form.photo.data.read()

        if form.tag.data == 'new_songs':
            cs = db.session.query(Choosen_Songs).order_by(Choosen_Songs.num.desc()).first()
            if cs == None:
                num = 0
            else:
                num = cs.num
            new_event.cs = num
        db.session.add(new_event)

        db.session.flush()
        db.session.commit()

        return redirect(url_for('events'))

    return render_template('add_event.html', voting_songs_or_groups=voting_songs_or_groups, form=form)


# Стриница События по id
@app.route('/event/<id>')
@login_required
def event(id):
    if Events.query.filter_by(id=id).count() == 0:
        return redirect(url_for('events'))

    event = Events.query.filter_by(id=id).first()
    if event.tag == 'new_songs':
        # Список песен выбранных в этом голосовании
        num = event.cs
        cs = Choosen_Songs.query.filter_by(num=num).all()
        songs=[]
        for i in cs:
            songs.append(Songs.query.filter_by(id=i.song_id).first())

        return render_template('new_songs.html', voting_songs_or_groups=voting_songs_or_groups, event=event, songs=songs)
    elif event.tag == 'new_group':
        return render_template('new_group.html', voting_songs_or_groups=voting_songs_or_groups, event=event,
                               group=Groups.query.filter_by(id=selected_group).first())

    return render_template('event.html', voting_songs_or_groups=voting_songs_or_groups, event=event)


# Картинка события
@app.route('/event_img/<event_id>')
def event_img(event_id):
    img = Events.query.filter_by(id=event_id).first().photo
    print(event_id, str(img)[:30])
    h = make_response(img)
    return h


# Страница уведомлений
@app.route('/notifications')
@login_required
def notifications():
    # Список доступных Уведомлений
    if current_user.get_position() not in ['chief', 'admin']:
        notifications = Notifications.query.filter((Notifications.access_level == 'all') |
                                                   (Notifications.access_level == position_groups.get(current_user.get_position())))
    else:
        notifications = Notifications.query
    notifications = notifications.order_by(Notifications.time.desc()).all()

    return render_template('notifications.html', voting_songs_or_groups=voting_songs_or_groups, notifications=notifications)


# Страница добавления уведомления
@app.route('/add_notification', methods=['GET', 'POST'])
@login_required
def add_notification():
    if current_user.get_position() == 'user':
        return redirect(url_for('notifications'))

    # Обработка формы
    form = Add_notification()
    if current_user.get_position() in ['chief', 'admin']:
        form.access_level.choices = [('local', 'Админы'), ('all', 'Все'), ('design', 'Дизайнеры'), ('tech', 'Техники')]
    else:
        form.access_level.choices = [('local', 'Отдел'), ('all', 'Все')]

    if form.validate_on_submit():
        access_level = form.access_level.data
        if form.access_level.data == 'local':
            access_level = position_groups.get(current_user.get_position())

        new_notification = Notifications(text=form.text.data, access_level=access_level, user_id=current_user.get_id())

        db.session.add(new_notification)
        db.session.commit()

        return redirect(url_for('notifications'))

    return render_template('add_notification.html', voting_songs_or_groups=voting_songs_or_groups, form=form)


# Трек песни
@app.route('/song_bell/<song_id>')
@login_required
def song_bell(song_id):
    return send_file(BytesIO(Songs.query.filter_by(id=song_id).first().bell), download_name=f'{Songs.query.filter_by(id=song_id).first().name}.mp3')


# Вспомогательная функция сброса bell-ов
@app.route('/return_bells')
@login_required
def return_bells():
    if voting_songs_or_groups == 'groups':
        for choice in Users_choices_groups.query.filter_by(user_id=current_user.get_id()).all():
            print('id - ' + str(choice.group_id))
            Groups.query.filter_by(id=choice.group_id).first().recent_likes -= choice.choice
            db.session.delete(choice)
            Users.query.filter_by(id=current_user.get_id()).first().bells = 10
    if voting_songs_or_groups == 'songs':
        for choice in Users_choices_songs.query.filter_by(user_id=current_user.get_id()).all():
            print('id - ' + str(choice.song_id))
            Songs.query.filter_by(id=choice.song_id).first().recent_likes -= choice.choice
            db.session.delete(choice)
            Users.query.filter_by(id=current_user.get_id()).first().bells = 10
    db.session.flush()
    db.session.commit()
    return redirect(url_for('voting'))


# @app.route('/test', methods=['GET', 'POST'])
# def test():
#     return render_template('test.html')


# port = int(os.environ.get('PORT', 5000))

if __name__ == '__main__':
    socketio.run(app, debug=True, port=4998)
