from flask import Blueprint, request, jsonify
from ..models.sale_model import create_sale
from ..utils.auth import token_required
from ..extension import mongo
import jwt
from flask import current_app as app

sales_bp = Blueprint('sales', __name__, url_prefix='/api/ventas')

# --- Crear venta ---
@sales_bp.route('', methods=['POST'])
@token_required
def create_venta_route():
    data = request.get_json()
    if not data.get('id_cliente') or not data.get('items'):
        return jsonify({"success": False, "message": "Datos incompletos"}), 400

    # Obtener id del vendedor desde el token
    token = request.headers.get('Authorization').replace("Bearer ", "")
    payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
    id_vendedor = payload['id']

    venta_id = create_sale(
        id_cliente=data['id_cliente'],
        items=data['items'],
        total=data.get('total', 0),
        id_vendedor=id_vendedor
    )

    return jsonify({"success": True, "message": "Venta creada correctamente", "venta_id": venta_id})

# --- Obtener ventas del vendedor ---
@sales_bp.route('', methods=['GET'])
@token_required
def get_ventas_vendedor():
    # Obtener id del vendedor desde el token
    token = request.headers.get('Authorization').replace("Bearer ", "")
    payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
    id_vendedor = payload['id']

    ventas_cursor = mongo.db.ventas.find({"id_vendedor": id_vendedor})
    ventas = []
    for v in ventas_cursor:
        ventas.append({
            "_id": str(v["_id"]),
            "id_cliente": v.get("id_cliente"),
            "productos": v.get("items", []),  # <- items como guardaste
            "total": v.get("total", 0),
            "fecha": v.get("created_at")      # <- coincide con create_sale
        })
    return jsonify(ventas)
