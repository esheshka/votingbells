from flask import render_template, url_for, redirect
# Скрипт, определяющий базу данных, импортируются таблицы
from database_creater import Users, Songs, Groups, Users_choices_songs, Users_choices_groups, Groups_Songs, Events, create_db, app, db
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
# Скрипт WTForms определяющий forms, упрощающий с ними работу
from forms_manager import Log_in_form, Sign_up_form, Add_song, Add_group, Add_event
# Скрипт, для получения данных о пользователе
from login_user import User_login
from flask_socketio import SocketIO, emit

login_manager = LoginManager(app)
login_manager.login_view = '/log_in'


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
    return render_template('voting_songs.html', selected_group=Groups.query.filter_by(id=selected_group).first().title,
                           voting_songs_or_groups=voting_songs_or_groups, songs=songs)


# Отправляем страницу голосования за тему
@app.route('/voting_groups')
@login_required
def voting_groups():
    groups = Groups.query.order_by(Groups.recent_likes.desc()).all()
    return render_template('voting_groups.html',  voting_songs_or_groups=voting_songs_or_groups, groups=groups)


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
                           titles=db.session.query(Songs.title).all(),
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
                           titles=db.session.query(Groups.title).all())


# Отправляем все список предложенных песен
# Функция доступна только пользователям 2 и выше уровня
@app.route('/approve_songs')
@login_required
def approve_songs():
    if current_user.get_position() in ['chief', 'admin']:
        return render_template('approve_songs.html', voting_songs_or_groups=voting_songs_or_groups,
                               songs=Songs.query.filter_by(approved=0).order_by(Songs.likes).all(),
                               titles=db.session.query(Songs.title).all(),
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
                               groups=Groups.query.filter_by(approved=0).order_by(Groups.likes).all(),
                               titles=db.session.query(Groups.title).all())
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
        try:
            hash = generate_password_hash(form.psw.data)
            u = Users(email=form.email.data, psw=hash)
            db.session.add(u)
            db.session.flush()
            db.session.commit()
            return redirect(url_for('log_in'))
        except:
            db.session.rollback()
            print("Ошибка добавления в БД")

        return redirect(url_for('voting'))

    return render_template('sign_up.html', voting_songs_or_groups=voting_songs_or_groups, form=form)


# Вход
@app.route('/log_in', methods=('POST', 'GET'))
def log_in():
    if current_user.is_authenticated:
        return redirect(url_for('profile'))
    form = Log_in_form()
    if form.validate_on_submit():
        if Users.query.filter_by(email=form.email.data).count() > 0 and check_password_hash(Users.query.filter_by(email=form.email.data).first().psw, form.psw.data):
            user_login = User_login().create(Users.query.filter_by(email=form.email.data).first())
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
    # for position in access_accordance:
    #     if position.get('name') == current_user.get_position():
    #         level = position.get('level')
    #         access.append(position.get('name'))
    #         break
    #
    # for position in access_accordance:
    #     if position.get('level') < level:
    #         access.append(position.get('name'))
    #     else:
    #         break
    #
    # if len(access)==1:
    #     taccess = str(tuple(access))[:-2] + ')'
    # else:
    #     taccess = str(tuple(access))
    if current_user.get_position() not in ['chief', 'admin']:
        events = Events.query.filter((Events.access_level == 'all') | (Events.access_level == position_groups.get(current_user.get_position()))).all()
    else:
        events = Events.query.all()
    # events = db.session.execute(f'SELECT * FROM events WHERE access_level IN {taccess};')
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
        if form.photo.data != '':
            new_event.photo = form.photo.data
        db.session.add(new_event)
        db.session.flush()
        db.session.commit()
        return redirect(url_for('events'))
    return render_template('add_event.html', voting_songs_or_groups=voting_songs_or_groups, form=form)


@app.route('/test')
def test():
    return render_template('test.html')


if __name__ == '__main__':
    app.run(debug=True)

