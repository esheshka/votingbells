from flask import render_template, url_for, redirect, request, make_response
# Скрипт, определяющий базу данных, импортируются таблицы
from database_creater import Users, Corp_Users, Songs, Groups, Users_choices_songs, Users_choices_groups, Groups_Songs, Events, create_db, app, db
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
# Скрипт WTForms определяющий forms, упрощающий с ними работу
from forms_manager import Log_in_form, Sign_up_form, Add_song, Add_group, Add_event
# Скрипт, для получения данных о пользователе
from login_user import User_login
from flask_socketio import SocketIO, emit
from base64 import b64encode
import smtplib
from email.mime.text import MIMEText
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadTimeSignature

login_manager = LoginManager(app)
login_manager.login_view = '/log_in'


s = URLSafeTimedSerializer(app.config['SECRET_KEY'])


socketio = SocketIO()
socketio.init_app(app)

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


# Отправляем страницу голосования за песни
@app.route('/voting_songs')
@login_required
def voting_songs():
    if voting_songs_or_groups == 'groups':
        return redirect(url_for('voting'))
    songs = []
    for song in Songs.query.order_by(Songs.recent_likes.desc()).all():
        if Groups_Songs.query.filter_by(song_id=song.id).filter_by(group_id=selected_group).count() > 0 or song.approved == 0:
            songs.append(song)
    user_likes = Users_choices_songs.query.filter_by(user_id=current_user.get_id())
    id_songs = db.session.query(Users_choices_songs.song_id).filter_by(user_id=current_user.get_id()).all()
    ids = []
    for m in id_songs:
        ids.append(str(m)[1:-2])
    user_selected_songs = Songs.query.filter(Songs.id.in_(ids)).order_by(Songs.recent_likes.desc()).all()
    return render_template('voting_songs.html', selected_group=Groups.query.filter_by(id=selected_group).first().title,
                           voting_songs_or_groups=voting_songs_or_groups, songs=songs,
                           user_likes=user_likes, user_selected_songs=user_selected_songs)


# Отправляем страницу голосования за тему
@app.route('/voting_groups')
@login_required
def voting_groups():
    # msg = Message('Hello', sender='as.yushinskiy@gmail.com', recipients=['as.yushinskiy@gmail.com'])
    # msg.body = "Hello Flask message sent from Flask-Mail"
    # mail.send(msg)


    groups = Groups.query.order_by(Groups.recent_likes.desc()).all()
    user_likes = Users_choices_groups.query.filter_by(user_id=current_user.get_id())
    id_groups = db.session.query(Users_choices_groups.group_id).filter_by(user_id=current_user.get_id()).all()
    ids = []
    for m in id_groups:
        ids.append(str(m)[1:-2])
    user_selected_groups = Groups.query.filter(Groups.id.in_(ids)).order_by(Groups.recent_likes.desc()).all()
    return render_template('voting_groups.html',  voting_songs_or_groups=voting_songs_or_groups, groups=groups,
                           user_likes=user_likes, user_selected_groups=user_selected_groups)


# Завершаем голосование и переходим к следующему
# Функция доступна только пользователям 2 и выше уровня
# Возвращает все временные переменные к изначальным значениям
@app.route('/change_voting')
@login_required
def change_voting():
    global selected_group
    global voting_songs_or_groups
    if current_user.get_position() == 'chief' or current_user.get_position() == 'admin':
        if voting_songs_or_groups == 'songs':
            voting_songs_or_groups = 'groups'
            Users_choices_groups.query.delete()
            db.session.execute('UPDATE users SET bells=10')
            db.session.execute('UPDATE groups SET recent_likes=0')
            db.session.commit()
            return redirect(url_for('voting_groups'))
        else:
            selected_group = Groups.query.order_by(Groups.recent_likes.desc()).first().id
            voting_songs_or_groups = 'songs'
            Users_choices_songs.query.delete()
            Songs.query.filter_by(approved=0).delete()
            db.session.execute('UPDATE songs SET offered_group="None"')
            db.session.execute('UPDATE users SET bells=10')
            db.session.execute('UPDATE songs SET recent_likes=0')
            db.session.commit()
            return redirect(url_for('voting_songs'))


# JS функция отвечающая за выставление пользователем оценки песни
@socketio.on('likes songs')
def likes_songs(data):
    another_choice = Users_choices_songs.query.filter_by(user_id=current_user.get_id()).filter_by(song_id=data[0])
    if another_choice.count() > 0:
        choice = another_choice.first()
        user = Users.query.filter_by(id=current_user.get_id()).first()
        if choice.choice*int(data[1]) >= 0:
            if current_user.get_bells() == 0:
                return 0
        else:
            user.bells = user.bells + 2
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
    count = Songs.query.filter_by(id=data[0]).first().recent_likes
    user_like = Users_choices_songs.query.filter_by(user_id=current_user.get_id()).filter_by(song_id=data[0]).first()
    if user_like == None:
        user_like = 0
    else:
        user_like = user_like.choice
    emit('show my likes song', [data[0], user_like])
    emit("vote totals songs", [count, data[0]], broadcast=True)
    emit('show bells', data=1, broadcast=True)


# JS функция отвечающая за выставление пользователем оценки теме
@socketio.on('likes groups')
def likes_groups(data):
    another_choice = Users_choices_groups.query.filter_by(user_id=current_user.get_id()).filter_by(group_id=data[0])
    if another_choice.count() > 0:
        choice = another_choice.first()
        user = Users.query.filter_by(id=current_user.get_id()).first()
        if choice.choice * int(data[1]) >= 0:
            if current_user.get_bells() == 0:
                return 0
        else:
            user.bells = user.bells + 2
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
    count = Groups.query.filter_by(id=data[0]).first().recent_likes
    user_like = Users_choices_groups.query.filter_by(user_id=current_user.get_id()).filter_by(group_id=data[0]).first()
    if user_like == None:
        user_like = 0
    else:
        user_like = user_like.choice
    emit('show my likes group', [data[0], user_like])
    emit("vote totals groups", [count, data[0]], broadcast=True)
    emit('show bells', data=1, broadcast=True)

# Отправляем страницу добавления песни
# Обрабатываем попытку добавить песню
@app.route('/add_song', methods=('POST', 'GET'))
@login_required
def add_song():
    global selected_group
    if voting_songs_or_groups == 'group':
        return redirect(url_for('404'))
    form = Add_song()
    if form.validate_on_submit():
        song = Songs.query.filter_by(title=form.title.data).filter_by(band=form.band.data)
        if song.count() > 0:
            if Groups_Songs.query.filter_by(song_id=song.first().id).filter_by(group_id=selected_group).count() > 0:
                print('There is the same song')
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


# Отправляем страницу добавления темы
# Обрабатываем попытку добавить тему
@app.route('/add_group', methods=('POST', 'GET'))
@login_required
def add_group():
    form = Add_group()
    if form.validate_on_submit():
        group = Groups.query.filter_by(title=form.title.data)
        if group.count() > 0:
            print('There is the same group')
        else:
            new_group = Groups(title=form.title.data)
            db.session.add(new_group)
            db.session.flush()
            db.session.commit()
            return redirect(url_for('voting'))
    return render_template('add_group.html', voting_songs_or_groups=voting_songs_or_groups, form=form,
                           titles=db.session.query(Groups.title).filter(Groups.approved == 1).all())


# Отправляем все список предложенных песен
# Функция доступна только пользователям 2 и выше уровня
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


# Отправляем все список предложенных тем
# Функция доступна только пользователям 2 и выше уровня
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
    emit("is approve group", [data[0], approved], broadcast=True)
    emit('show bells', data=1, broadcast=True)


@socketio.on('get bells')
def get_bells():
    emit('show bells self', current_user.get_bells())


# Страница песни по id
@app.route('/song/<id>')
@login_required
def song(id):
    groups = []
    for group in Groups_Songs.query.filter_by(song_id=id).all():
        groups.append(Groups.query.filter_by(id=group.group_id).first())
    return render_template('song.html', song=Songs.query.filter_by(id=id).first(), groups=groups, voting_songs_or_groups=voting_songs_or_groups)


# Страница темы по id
@app.route('/group/<id>')
@login_required
def group(id):
    songs = []
    for song in Groups_Songs.query.filter_by(group_id=id).all():
        songs.append(Songs.query.filter_by(id=song.song_id).first())
    return render_template('group.html', group=Groups.query.filter_by(id=id).first(), songs=songs, voting_songs_or_groups=voting_songs_or_groups)


# Вспомогательная функция, возвращающая bell-ы пользователям при не подтверждении песни за которую они голосовали
def return_bells_by_song(id):
    for choice in Users_choices_songs.query.filter_by(song_id=id):
        Users.query.filter_by(id=choice.user_id).first().bells += abs(choice.choice)

# Вспомогательная функция, возвращающая bell-ы пользователям при не подтверждении темы за которую они голосовали
def return_bells_by_group(id):
    for choice in Users_choices_groups.query.filter_by(group_id=id):
        print('reterns ' + str(abs(choice.choice)) + ' bells to ' + str(Users.query.filter_by(id=choice.user_id).first().id))
        Users.query.filter_by(id=choice.user_id).first().bells += abs(choice.choice)


# Регистрация
@app.route("/sign_up", methods=("POST", "GET"))
def sign_up():
    form = Sign_up_form()
    if form.validate_on_submit():
        corp_user = Corp_Users.query.filter_by(email=form.corp_email.data)
        if corp_user.count() == 0:
            return render_template('sign_up.html', voting_songs_or_groups=voting_songs_or_groups, form=form, error='Ученик не найден')
        else:
            try:
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

            token = s.dumps(form.corp_email.data, salt='email-confirm')
            link = url_for('confirm_email', token=token, external=True)
            sender = 'as.yushinskiy@gmail.com'
            password = 'clzaoekwnqguzmom'
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            try:
                server.login(sender, password)
                msg = MIMEText(link)
                msg['Subject'] = 'Click'
                server.sendmail(sender, form.corp_email.data, msg.as_string())
            except:
                print('плак')

            return 'Подтвердите свой email'

    return render_template('sign_up.html', voting_songs_or_groups=voting_songs_or_groups, form=form)


@app.route('/confirm_email/<token>')
def confirm_email(token):
    try:
        email = s.loads(token, salt='email-confirm', max_age=60)
    except SignatureExpired:
        return 'The token is expired'
    user = Users.query.filter_by(corp_email=email).first()
    user.confirmed = True
    db.session.commit()
    return redirect(url_for('log_in'))


# Вход
@app.route('/log_in', methods=('POST', 'GET'))
def log_in():
    if current_user.is_authenticated:
        return redirect(url_for('profile'))
    form = Log_in_form()
    if form.validate_on_submit():
        if Users.query.filter_by(login=form.login.data).count() > 0 and \
                check_password_hash(Users.query.filter_by(login=form.login.data).first().psw, form.psw.data):
            if Users.query.filter_by(login=form.login.data).first().confirmed == 0:
                return render_template('log_in.html', voting_songs_or_groups=voting_songs_or_groups, form=form, error='Подтвердите свою копоративную почту')
            user_login = User_login().create(Users.query.filter_by(login=form.login.data).first())
            login_user(user_login, remember=form.remember.data)
            return redirect(url_for('profile'))

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
    return render_template('profile.html', voting_songs_or_groups=voting_songs_or_groups)


# Страница событий
@app.route('/events')
@login_required
def events():
    access = []
    level = 0
    if current_user.get_position() not in ['chief', 'admin']:
        events = Events.query.filter((Events.access_level == 'all') | (Events.access_level == position_groups.get(current_user.get_position())))
    else:
        events = Events.query
    events = events.order_by(Events.time.desc())
    return render_template('events.html', voting_songs_or_groups=voting_songs_or_groups, events=events)


@app.route('/add_event', methods=['GET', 'POST'])
@login_required
def add_event():
    if current_user.get_position() == 'user':
        return redirect(url_for('events'))
    form = Add_event()
    if current_user.get_position() in ['chief', 'admin']:
        form.access_level.choices = [('local', 'Админы'), ('all', 'Все'), ('design', 'Дизайнеры'), ('tech', 'Техники')]
    else:
        form.access_level.choices = [('local', 'Отдел'), ('all', 'Все')]

    if form.validate_on_submit():
        access_level = form.access_level.data
        if form.access_level.data == 'local':
            access_level = position_groups.get(current_user.get_position())
        new_event = Events(title=form.title.data, tag=form.tag.data, text=form.text.data, access_level=access_level)
        if form.photo.data:
            new_event.photo = form.photo.data.read()
        db.session.add(new_event)
        db.session.commit()
        return redirect(url_for('events'))
    return render_template('add_event.html', voting_songs_or_groups=voting_songs_or_groups, form=form)


@app.route('/event_img/<event_id>')
def event_img(event_id):
    img = Events.query.filter_by(id=event_id).first().photo
    print(event_id, str(img)[:30])
    h = make_response(img)
    return h


@app.route('/test', methods=['GET', 'POST'])
def test():
    token = s.dumps('as.yushinskiy@gmail.com', salt='email-confirm')
    link = url_for('confirm_email', token=token, external=True)
    sender = 'as.yushinskiy@gmail.com'
    password = 'clzaoekwnqguzmom'
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    try:
        server.login(sender, password)
        msg = MIMEText(link)
        msg['Subject'] = 'Click'
        server.sendmail(sender, sender, msg.as_string())
        return 'success'
    except:
        return 'error'




if __name__ == '__main__':
    app.run(debug=True)

