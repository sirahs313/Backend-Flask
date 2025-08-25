from extension import mongo
from werkzeug.security import generate_password_hash, check_password_hash

class User:
    @staticmethod
    def create_user(name, email, password, role):
        hashed = generate_password_hash(password)
        return mongo.db.users.insert_one({
            "name": name,
            "email": email,
            "password": hashed,
            "role": role
        })

    @staticmethod
    def find_by_email(email):
        return mongo.db.users.find_one({"email": email})

    @staticmethod
    def check_password(user, password):
        return check_password_hash(user["password"], password)
