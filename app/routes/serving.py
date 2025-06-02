from flask import Blueprint, request, jsonify, Response, stream_with_context
from app.models import db, Order, OrderDetail
import json
import time
serving_bp = Blueprint('serving', __name__, url_prefix='/serving')


# ✅ GET /serving - 서빙할 항목 목록 불러오기
@serving_bp.route('', methods=['GET'])
def get_serving_orders():
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


# ✅ POST /serving/complete - 개별 항목 서빙 완료 처리
@serving_bp.route('/complete', methods=['POST'])
def complete_serving_item():
    data = request.get_json()
    order_detail_id = data.get('order_detail_id')

    if not order_detail_id:
        return jsonify({"error": "order_detail_id 누락"}), 400

    detail = OrderDetail.query.get(order_detail_id)
    if not detail:
        return jsonify({"error": "해당 항목이 존재하지 않습니다."}), 404

    detail.is_served = True
    db.session.commit()

    # 주문 전체 항목 서빙 완료 여부 확인
    order_id = detail.order_id
    remaining = OrderDetail.query.filter_by(order_id=order_id, is_served=False).count()

    if remaining == 0:
        order = Order.query.get(order_id)
        order.order_status = "완료"
        db.session.commit()

    return jsonify({
        "message": "항목 서빙 완료",
        "order_id": order_id,
        "fully_served": (remaining == 0)
    })

@serving_bp.route('/completeall', methods=['POST'])
def complete_entire_order():
    data = request.get_json()
    order_id = data.get('order_id')

    if not order_id:
        return jsonify({"error": "order_id 누락"}), 400

    order = Order.query.get(order_id)
    if not order:
        return jsonify({"error": "주문이 존재하지 않습니다."}), 404

    for item in order.order_details:
        item.is_served = True

    order.order_status = '완료'
    db.session.commit()

    return jsonify({
        "success": True,
        "order_id": order_id,
        "message": "주문 전체가 서빙 완료 처리되었습니다."
    })
    
@serving_bp.route('/sse', methods=['GET'])
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
