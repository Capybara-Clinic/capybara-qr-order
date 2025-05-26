from flask import Blueprint, request, jsonify, abort
from app.models import db, StoreTable, Order, OrderDetail, Menu

cashier_bp = Blueprint('cashier', __name__, url_prefix='/cashier')


# ✅ 전체 테이블 상태 조회
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


# ✅ 특정 테이블 주문 내역 조회
@cashier_bp.route('/table/<int:table_id>', methods=['GET'])
def get_table_orders(table_id):
    table = StoreTable.query.get(table_id)
    if not table:
        return abort(404, description="해당 테이블이 존재하지 않습니다.")

    orders = Order.query.filter_by(table_id=table_id).order_by(Order.created_at.desc()).all()

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


# ✅ 결제 확인 처리
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

    return jsonify({
        "message": "결제가 확인되었습니다.",
        "order_id": order_id
    })


# ✅ 수동 주문 등록 (캐셔용)
@cashier_bp.route('/manual_order', methods=['POST'])
def create_manual_order():
    data = request.get_json()
    table_id = data.get('table_id')
    depositor = data.get('depositor_name')
    items = data.get('items', [])

    if not table_id or not depositor or not items:
        return jsonify({"error": "필수 정보 누락"}), 400

    table = StoreTable.query.get(table_id)
    if not table:
        return jsonify({"error": "존재하지 않는 테이블입니다."}), 404

    table.is_occupied = True

    order = Order(
        table_id=table_id,
        depositor_name=depositor,
        total_amount=0,
        order_status='결제확인'  # 수동 주문은 바로 결제확인 처리
    )
    db.session.add(order)
    db.session.flush()

    total = 0
    for item in items:
        menu = Menu.query.get(item['menu_id'])
        if not menu or not menu.is_available:
            return jsonify({"error": f"{item['menu_id']}번 메뉴가 유효하지 않음"}), 400

        quantity = int(item['quantity'])
        unit_price = float(menu.price)
        subtotal = quantity * unit_price

        detail = OrderDetail(
            order_id=order.order_id,
            menu_id=menu.menu_id,
            quantity=quantity,
            unit_price=unit_price,
            subtotal=subtotal
        )
        db.session.add(detail)
        total += subtotal

    order.total_amount = total
    db.session.commit()

    return jsonify({
        "message": "수동 주문 등록 완료",
        "order_id": order.order_id
    }), 201


# ✅ 주문 수정 (항목 수량 변경, 메뉴 변경 등)
@cashier_bp.route('/order/update', methods=['PUT'])
def update_order():
    data = request.get_json()
    order_id = data.get('order_id')
    updated_items = data.get('items')

    order = Order.query.get(order_id)
    if not order:
        return jsonify({"error": "주문이 존재하지 않습니다."}), 404

    # 기존 상세 삭제 후 다시 추가
    OrderDetail.query.filter_by(order_id=order_id).delete()

    total = 0
    for item in updated_items:
        menu = Menu.query.get(item['menu_id'])
        if not menu:
            return jsonify({"error": f"{item['menu_id']}번 메뉴가 없습니다."}), 400

        quantity = int(item['quantity'])
        unit_price = float(menu.price)
        subtotal = quantity * unit_price

        new_detail = OrderDetail(
            order_id=order_id,
            menu_id=menu.menu_id,
            quantity=quantity,
            unit_price=unit_price,
            subtotal=subtotal
        )
        db.session.add(new_detail)
        total += subtotal

    order.total_amount = total
    db.session.commit()

    return jsonify({
        "message": "주문이 수정되었습니다.",
        "order_id": order_id
    })

@cashier_bp.route('/order/delete', methods=['DELETE'])
def cancel_order():
    data = request.get_json()
    order_id = data.get('order_id')

    order = Order.query.get(order_id)
    if not order:
        return jsonify({"error": "해당 주문이 존재하지 않습니다."}), 404

    order.order_status = "취소"
    db.session.commit()

    return jsonify({
        "message": "주문이 취소되었습니다.",
        "order_id": order_id
    })