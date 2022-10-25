from flask import Flask, render_template, url_for, request, flash, session, redirect, abort, g, make_response, jsonify
from flask_sqlalchemy import SQLAlchemy
from database_creater import Users, Songs, Groups, Users_choices_songs, Users_choices_groups, Groups_Songs, Events, create_db, app, db
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from forms_manager import Log_in_form, Sign_up_form, Add_song, Add_group
from login_user import User_login
from flask_socketio import SocketIO, emit
import os
import requests


login_manager = LoginManager(app)
login_manager.login_view = '/log_in'


socketio = SocketIO()
socketio.init_app(app)


voting_songs_or_groups = 'groups'


access_accordance = (
    {'name': 'user', 'level': 0},
    {'name': 'designer', 'level': 1},
    {'name': 'placer', 'level': 1},
    {'name': 'cutter', 'level': 1},
    {'name': 'text_writer', 'level': 1},
    {'name': 'supporter', 'level': 1},
    {'name': 'coordinator_design', 'level': 1},
    {'name': 'coordinator_tech', 'level': 1},
    {'name': 'admin', 'level': 2},
    {'name': 'chief', 'level': 3})

menu = (
    {'title': 'Зарегистрироваться', 'url': '/sign_up'},
    {'title': 'Войти', 'url': '/log_in'},
    {'title': 'Выйти', 'url': '/log_out'},
    {'title': 'Голосование', 'url': '/voting'},
    {'title': 'Профиль', 'url': '/profile'},
    {'title': 'Добавить тему', 'url': '/add_group'},
    {'title': 'Проверить темы', 'url': '/approve_groups'},
    {'title': 'Добавить песню', 'url': '/add_song'},
    {'title': 'Проверить песни', 'url': '/approve_songs'})

selected_group = 1



@login_manager.user_loader
def load_user(user_id):
    print('load_user ' + user_id)
    return User_login().fromDB(Users.query.filter_by(id=user_id).first())


@app.route('/')
@app.route('/voting')
@login_required
def voting():
    if voting_songs_or_groups == 'songs':
        return redirect(url_for('voting_songs'))
    else:
        return redirect(url_for('voting_groups'))


@app.route('/voting_songs')
@login_required
def voting_songs():
    songs = Songs.query.order_by(Songs.recent_likes.desc()).all()
    return render_template('voting_songs.html', selected_group=Groups.query.filter_by(id=selected_group).first().title,
                           voting_songs_or_groups=voting_songs_or_groups, songs=songs)


@app.route('/voting_groups')
@login_required
def voting_groups():
    groups = Groups.query.order_by(Groups.recent_likes.desc()).all()
    return render_template('voting_groups.html',  voting_songs_or_groups=voting_songs_or_groups, groups=groups)


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
    emit("vote totals songs", [count, data[0], current_user.get_bells()], broadcast=True)


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
    emit("vote totals groups", [count, data[0], current_user.get_bells()], broadcast=True)


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
            if Groups_Songs.query.filter_by(song_id=song.first().id).filter_by(group_id=selected_group).count() == 0:
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
    return render_template('add_song.html', voting_songs_or_groups=voting_songs_or_groups, form=form)


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
    return render_template('add_group.html', voting_songs_or_groups=voting_songs_or_groups, form=form)


@app.route('/approve_songs')
@login_required
def approve_songs():
    return render_template('approve_songs.html', voting_songs_or_groups=voting_songs_or_groups, songs=Songs.query.filter_by(approved=0).order_by(Songs.likes).all())


@app.route('/approve_groups')
@login_required
def approve_groups():
    return render_template('approve_groups.html', voting_songs_or_groups=voting_songs_or_groups, groups=Groups.query.filter_by(approved=0).order_by(Groups.likes).all())


@socketio.on('approve song')
@login_required
def approve_song(data):
    song = Songs.query.filter_by(id=data[0]).first()
    song.approved = 1
    if data[1] == 'Yes':
        gs = Groups_Songs(song_id=data[0], group_id=selected_group)
        db.session.add(gs)
    elif Groups_Songs.query.filter_by(song_id=data[0]).count() == 0:
        return_bells_by_song(data[0])
        song.recent_bells = 0
        db.session.delete(song)
    db.session.flush()
    db.session.commit()
    emit("is approve song", [data[0]], broadcast=True)


@socketio.on('approve group')
@login_required
def approve_group(data):
    group = Groups.query.filter_by(id=data[0]).first()
    group.approved = 1
    if data[1] == 'No':
        return_bells_by_group(data[0])
        group.recent_bells = 0
        db.session.delete(group)
    db.session.flush()
    db.session.commit()
    emit("is approve group", [data[0]], broadcast=True)


@app.route('/song/<id>')
def song(id):
    return render_template('song.html', song=Songs.query.filter_by(id=id).first(), voting_songs_or_groups=voting_songs_or_groups)


def return_bells_by_song(id):
    for choice in Users_choices_songs.query.filter_by(song_id=id):
        Users.query.filter_by(id=choice.user_id).first().bells += abs(choice.choice)

def return_bells_by_group(id):
    for choice in Users_choices_groups.query.filter_by(group_id=id):
        Users.query.filter_by(id=choice.user_id).first().bells += abs(choice.choice)


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


@app.route('/log_in', methods=('POST', 'GET'))
def log_in():
    if current_user.is_authenticated:
        return redirect(url_for('profile'))
    form = Log_in_form()
    if form.validate_on_submit():
        if check_password_hash(Users.query.filter_by(email=form.email.data).first().psw, form.psw.data):
            user_login = User_login().create(Users.query.filter_by(email=form.email.data).first())
            login_user(user_login, remember=form.remember.data)
            return redirect(url_for('profile'))

    return render_template('log_in.html', voting_songs_or_groups=voting_songs_or_groups, form=form)


@app.route('/log_out', methods=('POST', 'GET'))
@login_required
def log_out():
    logout_user()
    return redirect(url_for('log_in'))


@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html', voting_songs_or_groups=voting_songs_or_groups)


@app.route('/events')
@login_required
def events():
    access = []
    level = 0
    for position in access_accordance:
        if position.get('name') == current_user.get_position():
            level = position.get('level')
            access.append(position.get('name'))
            break

    for position in access_accordance:
        if position.get('level') < level:
            access.append(position.get('name'))
        else:
            break
    if len(access)==1:
        taccess = str(tuple(access))[:-2] + ')'
    else:
        taccess = str(tuple(access))
    print(taccess)
    events = db.session.execute(f'SELECT * FROM events WHERE access_level IN {taccess};')
    return render_template('events.html', voting_songs_or_groups=voting_songs_or_groups, events=events)


@app.route('/test')
def test():
    return render_template('test.html')


if __name__ == '__main__':
    app.run(debug=True)

