from flask import url_for


class User_login():
    def fromDB(self, user):
        self.__user = user
        return self

    def create(self, user):
        self.__user = user
        return self

    def is_authenticated(self):
        return True

    def is_active(self):
        return True

    def is_anonymous(self):
        return False


    def get_id(self):
        return str(self.__user.id) if self.__user else None

    def get_email(self):
        return self.__user.email if self.__user else None

    def get_avatar(self, app):
        img = None
        if not self.__user.avatar:
            try:
                with app.open_resource(app.root_path + url_for('static', filename='img/default.png'), 'rb') as f:
                    img = f.read()
            except FileNotFoundError as e:
                print('Default avatar not found ' + str(e))
        else:
            img = self.__user.avatar
        return img

    def get_position(self):
        return self.__user.position if self.__user else None

    def get_bells(self):
        return self.__user.bells if self.__user else 0


    def is_png(self, filename):
        ext = filename.rsplit('.', 1)[1]
        if ext == 'png' or ext == 'PNG':
            return 1
        return 0