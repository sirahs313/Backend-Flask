from flask import Blueprint, request, jsonify
from extension import mongo
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
from datetime import datetime, timedelta

auth_bp = Blueprint("auth", __name__)
SECRET = "tu_secreto_para_jwt"

@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    name = data.get("name")
    email = data.get("email")
    password = data.get("password")
    role = data.get("role")

    if not all([name, email, password, role]):
        return jsonify({"error": "Faltan datos"}), 400

    if mongo.db.users.find_one({"email": email}):
        return jsonify({"error": "Usuario ya existe"}), 400

    hashed = generate_password_hash(password)
    mongo.db.users.insert_one({"name": name, "email": email, "password": hashed, "role": role})
    return jsonify({"message": "Usuario registrado correctamente"}), 201

@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")

    user = mongo.db.users.find_one({"email": email})
    if not user or not check_password_hash(user["password"], password):
        return jsonify({"success": False, "message": "Credenciales incorrectas"}), 401

    token = jwt.encode({"id": str(user["_id"]), "role": user["role"], "exp": datetime.utcnow() + timedelta(hours=1)}, SECRET, algorithm="HS256")
    return jsonify({"success": True, "token": token, "role": user["role"], "name": user["name"]})
