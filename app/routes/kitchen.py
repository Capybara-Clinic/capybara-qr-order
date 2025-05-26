from flask import Blueprint, jsonify
from app.models import Order, OrderDetail

kitchen_bp = Blueprint('kitchen', __name__, url_prefix='/kitchen')


@kitchen_bp.route('', methods=['GET'])
def get_kitchen_orders():
    orders = Order.query.filter_by(order_status="결제확인").order_by(Order.created_at.asc()).all()
    result = []

    for order in orders:
        details = OrderDetail.query.filter_by(order_id=order.order_id, is_served=False).all()
        item_list = []

        for d in details:
            item_list.append({
                "order_detail_id": d.order_detail_id,
                "table_id": order.table_id,
                "menu_name": d.menu.menu_name,
                "quantity": d.quantity,
                "is_served": d.is_served
            })

        if item_list:
            result.append({
                "order_id": order.order_id,
                "order_time": order.order_time.strftime("%Y-%m-%d %H:%M:%S"),
                "items": item_list
            })

    return jsonify(result)