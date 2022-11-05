from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import os
import datetime


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SECRET_KEY'] = 'asdfghhgfdsaadfhfhgdjrebcvndffh'
# app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")
# print(app.config["SECRET_KEY"])
app.config['JWT_ALGORITHM'] = 'HS256'
db = SQLAlchemy(app)


class Users(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(50), unique=True)
    psw = db.Column(db.String(500), nullable=True)
    bells = db.Column(db.Integer, default=10)
    position = db.Column(db.String, default='user')
    confirmed = db.Column(db.Boolean, nullable=False, default=False)


class Songs(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=True)
    band = db.Column(db.String(100), nullable=True)
    bell = db.Column(db.LargeBinary, default=None)
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
    title = db.Column(db.String(50))
    tag = db.Column(db.String(500))
    photo = db.Column(db.LargeBinary, default=None)
    text = db.Column(db.String(500))
    access_level = db.Column(db.String(50))
    time = db.Column(db.DateTime, default=datetime.datetime.now())

def create_db():
    global db
    global app
    with app.app_context():
        db.create_all()