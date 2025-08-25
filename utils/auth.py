from functools import wraps
from flask import request, jsonify
import jwt

SECRET = "tu_secreto_para_jwt"

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get("Authorization")
        if not token:
            return jsonify({"error": "Token requerido"}), 401
        try:
            token = token.split(" ")[1]
            data = jwt.decode(token, SECRET, algorithms=["HS256"])
            request.user = data
        except:
            return jsonify({"error": "Token inválido"}), 401
        return f(*args, **kwargs)
    return decorated

def roles_required(*roles):
    def wrapper(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if request.user["role"] not in roles:
                return jsonify({"error": "Acceso denegado"}), 403
            return f(*args, **kwargs)
        return decorated
    return wrapper
