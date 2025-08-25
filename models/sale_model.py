# models/sale_model.py
from ..extension import mongo
import datetime

def create_sale(id_cliente, items, total, id_vendedor):
    venta_doc = {
        "id_cliente": id_cliente,
         "id_vendedor": id_vendedor,  # <- aquí
        "items": items,  # items = [{"product_id": ..., "quantity": ..., "price": ...}]
        "total": total,
        "created_at": datetime.datetime.utcnow()
    }
    result = mongo.db.ventas.insert_one(venta_doc)
    return str(result.inserted_id)
