from flask import url_for


class User_login():
    def fromDB(self, user):
        self.__user = user
        return self

    def create(self, user):
        self.__user = user
        return self

    def is_authenticated(self):
        if self.__user and self.__user.confirmed:
            return True
        return False

    def is_active(self):
        return True

    def is_anonymous(self):
        return False


    def get_id(self):
        return str(self.__user.id) if self.__user else None

    def get_login(self):
        return self.__user.login if self.__user else None

    def get_position(self):
        return self.__user.position if self.__user else None

    def get_bells(self):
        return self.__user.bells if self.__user else 0


    def is_png(self, filename):
        ext = filename.rsplit('.', 1)[1]
        if ext == 'png' or ext == 'PNG':
            return 1
        return 0