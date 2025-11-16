from passlib.hash import pbkdf2_sha256
from user import User

def authenticate(username, password):
    user = User.find_by_username(username)
    if user and pbkdf2_sha256.verify(password, user.password):
        return user

def identity(payload):
    user_id = payload['identity']
    return User.find_by_id(user_id)
