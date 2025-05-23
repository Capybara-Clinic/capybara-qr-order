from flask import Blueprint, request, jsonify
from app.models import db, Order, OrderDetail, StoreTable, Menu

order_bp = Blueprint('order', __name__, url_prefix='/order')

@order_bp.route('/submit', methods=['POST'])
def submit_order():
    data = request.get_json()
    table_id = data.get('table_id')
    depositor = data.get('depositor')
    items = data.get('items', [])

    if not table_id or not depositor or not items:
        return jsonify({"error": "필수 정보가 누락되었습니다."}), 400

    # 1. 테이블 유효성 확인
    table = StoreTable.query.get(table_id)
    if not table:
        return jsonify({"error": "존재하지 않는 테이블입니다."}), 404

    # 2. 테이블 사용중으로 설정
    if not table.is_occupied:
        table.is_occupied = True
        db.session.add(table)

    # 3. 주문 생성
    order = Order(
        table_id=table_id,
        depositor_name=depositor,
        total_amount=0,
        order_status='결제대기'
    )
    db.session.add(order)
    db.session.flush()  # order_id 확보

    total = 0
    for item in items:
        menu = Menu.query.get(item['menu_id'])
        if not menu or not menu.is_available:
            return jsonify({"error": f"{item['menu_id']}번 메뉴를 찾을 수 없거나 품절입니다."}), 400

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
        "message": "주문이 접수되었습니다.",
        "order_id": order.order_id
    }), 201

@order_bp.route('/payment_info/<int:order_id>', methods=['GET'])
def get_payment_info(order_id):
    order = Order.query.get(order_id)
    if not order:
        return jsonify({"error": "주문이 존재하지 않습니다."}), 404

    details = OrderDetail.query.filter_by(order_id=order_id).all()
    detail_data = [
        {
            "menu_name": d.menu.menu_name,
            "quantity": d.quantity,
            "subtotal": float(d.subtotal)
        } for d in details
    ]

    return jsonify({
        "order_id": order_id,
        "depositor_name": order.depositor_name,
        "total_amount": float(order.total_amount),
        "items": detail_data
    })