# app.py
from flask import Flask, request, jsonify
from flask_pymongo import PyMongo
from flask_cors import CORS
import bcrypt
import jwt
import datetime
from functools import wraps
from bson import ObjectId

# Crear la app
app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Configuración MongoDB y JWT
app.config['MONGO_URI'] = "mongodb+srv://ericksuacos30:313420313@clustereyhs.rik7vbx.mongodb.net/tienda?retryWrites=true&w=majority"
app.config['SECRET_KEY'] = 'tu_secreto_para_jwt'

mongo = PyMongo(app)
users = mongo.db.users  # Colección de usuarios
ventas = mongo.db.ventas  # Colección de ventas

# --- Decorador para verificar token ---
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({"message": "Token faltante"}), 401
        try:
            token = token.replace("Bearer ", "")
            jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
        except:
            return jsonify({"message": "Token inválido"}), 401
        return f(*args, **kwargs)
    return decorated

# --- Registro de usuario ---
@app.route('/api/auth/register', methods=['POST'])
def register():
    data = request.get_json()
    name = data.get('name')
    email = data.get('email')
    password = data.get('password')
    role = data.get('role', 'cliente')

    if users.find_one({"email": email}):
        return jsonify({"success": False, "message": "El usuario ya existe"}), 400

    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

    users.insert_one({
        "name": name,
        "email": email,
        "password": hashed_password,
        "role": role
    })

    return jsonify({"success": True, "message": "Usuario registrado correctamente"}), 201

# --- Login de usuario ---
@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    user = users.find_one({"email": email})
    if not user or not bcrypt.checkpw(password.encode('utf-8'), user['password']):
        return jsonify({"success": False, "message": "Credenciales incorrectas"}), 401

    token = jwt.encode(
        {
            "id": str(user['_id']),
            "role": user['role'],
            "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1)
        },
        app.config['SECRET_KEY'],
        algorithm="HS256"
    )

    return jsonify({
        "success": True,
        "token": token,
        "role": user['role'],
        "name": user['name']
    })

# --- Traer solo clientes ---
@app.route('/api/users/clientes', methods=['GET'])
@token_required
def get_clientes():
    clientes_cursor = users.find({"role": "cliente"})
    clientes = []
    for c in clientes_cursor:
        clientes.append({
            "_id": str(c["_id"]),
            "name": c["name"],
            "email": c["email"]
        })
    return jsonify(clientes), 200
# --- Crear una venta ---
@app.route('/api/ventas', methods=['POST'])
@token_required
def create_venta():
    token = request.headers.get('Authorization').replace("Bearer ", "")
    payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
    id_vendedor = str(payload['id'])  # ✅ aseguramos string

    data = request.get_json()
    if not data.get('id_cliente') or not data.get('items'):
        return jsonify({"success": False, "message": "Datos incompletos"}), 400

    venta_doc = {
        "id_cliente": ObjectId(data['id_cliente']),
        "id_vendedor": id_vendedor,  # ✅ guardamos como string
        "items": data['items'],
        "total": data.get('total', 0),
        "created_at": datetime.datetime.utcnow()
    }

    result = ventas.insert_one(venta_doc)

    return jsonify({
        "success": True,
        "message": "Venta creada correctamente",
        "venta_id": str(result.inserted_id)
    }), 201


# --- Obtener ventas ---
@app.route('/api/ventas', methods=['GET'])
@token_required
def get_ventas():
    token = request.headers.get('Authorization').replace("Bearer ", "")
    payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
    id_vendedor = str(payload['id'])
    role = payload['role']

    # Si es admin, trae todas las ventas, si no, solo las del vendedor
    query = {} if role == 'admin' else {"id_vendedor": id_vendedor}
    ventas_cursor = ventas.find(query)

    ventas_list = []
    for v in ventas_cursor:
        cliente = users.find_one({"_id": v.get('id_cliente')})
        vendedor = users.find_one({"_id": ObjectId(v.get('id_vendedor'))}) if v.get('id_vendedor') else None
        ventas_list.append({
            "_id": str(v["_id"]),
            "id_cliente": {"name": cliente["name"]} if cliente else None,
            "id_vendedor": {"name": vendedor["name"]} if vendedor else None,
            "productos": [
                {
                    "id_producto": p.get("product_id"),
                    "descripcion": p.get("descripcion", ""),
                    "cantidad": p.get("quantity", 0),
                    "price": float(p.get("price", 0))
                } for p in v.get("items", [])
            ],
            "total": float(v.get("total", 0)),
            "fecha": v.get("created_at").isoformat() if v.get("created_at") else None
        })
    return jsonify(ventas_list), 200

 


# --- Obtener compras del cliente ---
@app.route('/api/ventas/mis-compras', methods=['GET'])
@token_required
def get_mis_compras():
    token = request.headers.get('Authorization').replace("Bearer ", "")
    payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
    id_cliente = payload['id']  # ⚡ el id del cliente logueado

    ventas_cursor = ventas.find({"id_cliente": ObjectId(id_cliente)})
    compras_list = []
    for v in ventas_cursor:
        vendedor = users.find_one({"_id": ObjectId(v.get('id_vendedor'))})
        compras_list.append({
            "_id": str(v["_id"]),
            "id_vendedor": {"name": vendedor["name"]} if vendedor else None,
            "productos": [
                {
                    "product_id": p.get("product_id"),
                    "descripcion": p.get("descripcion", ""),
                    "cantidad": p.get("quantity", 0),
                    "price": float(p.get("price", 0))
                } for p in v.get("items", [])
            ],
            "total": float(v.get("total", 0)),
            "fecha": v.get("created_at").isoformat() if v.get("created_at") else None
        })
    return jsonify(compras_list), 200

@app.route('/api/reportes/ventas', methods=['GET'])
@token_required
def reporte_ventas():
    ventas_cursor = ventas.find()
    totalVentas = 0
    totalItems = 0
    ingresos = 0
    ganancias = 0  # puedes calcular margen si tienes info de costo

    ventasPorDia = {}
    ventasPorUsuario = {}
    productosMasVendidos = {}

    for v in ventas_cursor:
        totalVentas += 1
        items = v.get('items', [])
        totalItems += sum([p.get('quantity', 0) for p in items])
        ingresos += sum([float(p.get('price', 0)) * p.get('quantity', 0) for p in items])
        ganancias += sum([float(p.get('price', 0)) * p.get('quantity', 0) * 0.3 for p in items])  # ejemplo 30% ganancia

        fecha = v.get('created_at').strftime("%Y-%m-%d") if v.get('created_at') else "Sin Fecha"
        ventasPorDia.setdefault(fecha, {"ventas": 0, "items": 0, "ingresos": 0, "ganancias": 0})
        ventasPorDia[fecha]["ventas"] += 1
        ventasPorDia[fecha]["items"] += sum([p.get('quantity', 0) for p in items])
        ventasPorDia[fecha]["ingresos"] += sum([float(p.get('price', 0)) * p.get('quantity', 0) for p in items])
        ventasPorDia[fecha]["ganancias"] += sum([float(p.get('price', 0)) * p.get('quantity', 0) * 0.3 for p in items])

        id_vendedor = str(v.get('id_vendedor'))
        usuario = users.find_one({"_id": ObjectId(id_vendedor)})
        nombre_usuario = usuario["name"] if usuario else "Desconocido"
        ventasPorUsuario.setdefault(nombre_usuario, {"ventas": 0, "items": 0, "ingresos": 0, "ganancias": 0})
        ventasPorUsuario[nombre_usuario]["ventas"] += 1
        ventasPorUsuario[nombre_usuario]["items"] += sum([p.get('quantity', 0) for p in items])
        ventasPorUsuario[nombre_usuario]["ingresos"] += sum([float(p.get('price', 0)) * p.get('quantity', 0) for p in items])
        ventasPorUsuario[nombre_usuario]["ganancias"] += sum([float(p.get('price', 0)) * p.get('quantity', 0) * 0.3 for p in items])

        for p in items:
            prod_id = p.get('product_id')
            if not prod_id:
                continue
            if prod_id not in productosMasVendidos:
                productosMasVendidos[prod_id] = {"descripcion": p.get('descripcion', ''), "cantidad": 0, "ingresos": 0, "ganancias": 0}
            productosMasVendidos[prod_id]["cantidad"] += p.get('quantity', 0)
            productosMasVendidos[prod_id]["ingresos"] += float(p.get('price', 0)) * p.get('quantity', 0)
            productosMasVendidos[prod_id]["ganancias"] += float(p.get('price', 0)) * p.get('quantity', 0) * 0.3

    return jsonify({
        "totalVentas": totalVentas,
        "totalItems": totalItems,
        "ingresos": ingresos,
        "ganancias": ganancias,
        "ventasPorDia": ventasPorDia,
        "ventasPorUsuario": ventasPorUsuario,
        "productosMasVendidos": list(productosMasVendidos.values())
    })

#obtener usuarios
@app.route('/api/users', methods=['GET'])
@token_required
def get_users():
    users_cursor = users.find()
    users_list = []
    for u in users_cursor:
        users_list.append({
            "_id": str(u["_id"]),
            "name": u["name"],
            "email": u["email"],
            "role": u.get("role", "cliente")
        })
    return jsonify(users_list), 200
#Crear usuario
@app.route('/api/users', methods=['POST'])
@token_required
def create_user():
    data = request.get_json()
    name = data.get('name')
    email = data.get('email')
    password = data.get('password')
    role = data.get('role', 'cliente')

    if not all([name, email, password]):
        return jsonify({"success": False, "message": "Datos incompletos"}), 400

    if users.find_one({"email": email}):
        return jsonify({"success": False, "message": "El usuario ya existe"}), 400

    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    users.insert_one({
        "name": name,
        "email": email,
        "password": hashed_password,
        "role": role
    })
    return jsonify({"success": True, "message": "Usuario creado"}), 201
# actualizar usuario
@app.route('/api/users/<id>', methods=['PUT'])
@token_required
def update_user(id):
    data = request.get_json()
    update_data = {
        "name": data.get("name"),
        "email": data.get("email"),
        "role": data.get("role")
    }
    if data.get("password"):
        update_data["password"] = bcrypt.hashpw(data["password"].encode('utf-8'), bcrypt.gensalt())
    result = users.update_one({"_id": ObjectId(id)}, {"$set": update_data})
    if result.modified_count == 0:
        return jsonify({"success": False, "message": "Usuario no modificado"}), 400
    return jsonify({"success": True, "message": "Usuario actualizado"}), 200


#Eliminar usuario
@app.route('/api/users/<id>', methods=['DELETE'])
@token_required
def delete_user(id):
    result = users.delete_one({"_id": ObjectId(id)})
    if result.deleted_count == 0:
        return jsonify({"success": False, "message": "Usuario no encontrado"}), 404
    return jsonify({"success": True, "message": "Usuario eliminado"}), 200

#Ver ventas en dashboardadmin
@app.route('/api/ventas/all', methods=['GET'])
@token_required
def get_all_ventas():
    token = request.headers.get('Authorization').replace("Bearer ", "")
    payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
    
    if payload['role'] != 'admin':
        return jsonify({"success": False, "message": "No autorizado"}), 403

    ventas_cursor = ventas.find()
    ventas_list = []
    for v in ventas_cursor:
        cliente = users.find_one({"_id": v.get('id_cliente')})
        vendedor = users.find_one({"_id": ObjectId(v.get('id_vendedor'))}) if v.get('id_vendedor') else None
        ventas_list.append({
            "_id": str(v["_id"]),
            "id_cliente": {"name": cliente["name"]} if cliente else None,
            "id_vendedor": {"name": vendedor["name"]} if vendedor else None,
            "productos": [
                {
                    "id_producto": p.get("product_id"),
                    "descripcion": p.get("descripcion", ""),
                    "cantidad": p.get("quantity", 0),
                    "price": float(p.get("price", 0))
                } for p in v.get("items", [])
            ],
            "total": float(v.get("total", 0)),
            "fecha": v.get("created_at").isoformat() if v.get("created_at") else None
        })
    return jsonify(ventas_list), 200

# --- Ejecutar servidor ---
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)
