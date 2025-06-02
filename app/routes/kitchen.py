from flask import Blueprint, jsonify, Response, stream_with_context
from app.models import Order, OrderDetail
import json
import time
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

@kitchen_bp.route('/sse', methods=['GET'])
def order_stream():
    def event_stream():
        last_sent_id = 0
        while True:
            new_orders = Order.query.filter(
                Order.order_status == "결제확인",
                Order.order_id > last_sent_id  
            ).order_by(Order.order_id).all()

            for order in new_orders:
                details = OrderDetail.query.filter_by(order_id=order.order_id).all()
                order_dict = {
                    "order_id": order.order_id,
                    "table_id": order.table_id,
                    "depositor_name": order.depositor_name,
                    "total_amount": float(order.total_amount),
                    "order_status": order.order_status,
                    "order_time": str(order.order_time),
                    "created_at": str(order.created_at),
                    "details": [
                        {
                            "order_detail_id": d.order_detail_id,
                            "menu_id": d.menu_id,
                            "menu_name": d.menu.menu_name,
                            "quantity": d.quantity,
                            "unit_price": float(d.unit_price),
                            "subtotal": float(d.subtotal),
                            "is_served": d.is_served
                        } for d in details
                    ]
                }
                yield f"data: {json.dumps(order_dict, ensure_ascii=False)}\n\n"
                last_sent_id = order.order_id

            time.sleep(3)  # 클라이언트에 주기적으로 업데이트 (3초 간격)

    return Response(stream_with_context(event_stream()), content_type='text/event-stream')