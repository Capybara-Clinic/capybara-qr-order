from flask import Blueprint, request, jsonify, abort
from app.models import db, StoreTable, Order, OrderDetail, Menu

cashier_bp = Blueprint('cashier', __name__, url_prefix='/cashier')


@cashier_bp.route('/tables', methods=['GET'])
def get_table_statuses():
    tables = StoreTable.query.order_by(StoreTable.table_id).all()
    result = []

    for table in tables:
        latest_order = (
            Order.query.filter_by(table_id=table.table_id)
            .order_by(Order.created_at.desc())
            .first()
        )
        result.append({
            "table_id": table.table_id,
            "is_occupied": table.is_occupied,
            "latest_order_status": latest_order.order_status if latest_order else None
        })

    return jsonify(result)


@cashier_bp.route('/table/<int:table_id>', methods=['GET'])
def get_table_orders(table_id):
    table = StoreTable.query.get(table_id)
    if not table:
        return abort(404, description="해당 테이블이 존재하지 않습니다.")

    orders = (
        Order.query.filter_by(table_id=table_id)
        .order_by(Order.created_at.desc())
        .all()
    )

    result = []
    for order in orders:
        details = OrderDetail.query.filter_by(order_id=order.order_id).all()
        detail_data = [
            {
                "menu_name": d.menu.menu_name,
                "quantity": d.quantity,
                "is_served": d.is_served
            } for d in details
        ]
        result.append({
            "order_id": order.order_id,
            "depositor_name": order.depositor_name,
            "order_status": order.order_status,
            "total_amount": float(order.total_amount),
            "order_time": order.order_time.strftime("%Y-%m-%d %H:%M:%S"),
            "details": detail_data
        })

    return jsonify({
        "table_id": table_id,
        "orders": result
    })


@cashier_bp.route('/confirm_order', methods=['POST'])
def confirm_order():
    data = request.get_json()
    order_id = data.get('order_id')

    order = Order.query.get(order_id)
    if not order:
        return jsonify({"error": "주문이 존재하지 않습니다."}), 404

    if order.order_status != "결제대기":
        return jsonify({"error": "이미 처리된 주문입니다."}), 400

    order.order_status = "결제확인"
    db.session.commit()

    #  SSE로 주방/서빙에 전송 처리 가능

    # return jsonify({
    #     "message": "결제가 확인되었습니다.",
    #     "order_id": order_id
    # })