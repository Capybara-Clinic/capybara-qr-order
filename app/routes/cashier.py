from flask import Blueprint, request, jsonify, abort
from app.models import db, StoreTable, Order, OrderDetail, Menu

cashier_bp = Blueprint('cashier', __name__, url_prefix='/cashier')


# 전체 테이블 상태 조회
@cashier_bp.route('/tables', methods=['GET'])
def get_table_statuses():
    tables = StoreTable.query.order_by(StoreTable.table_id).all()
    result = []

    for table in tables:
        # 마지막 초기화 시점 (비어 있을 경우)
        last_reset_time = table.updated_at if not table.is_occupied else None

        # 주문 필터링: 마지막 초기화 이후만 포함
        if last_reset_time:
            orders = Order.query.filter(
                Order.table_id == table.table_id,
                Order.created_at > last_reset_time
            ).all()
        else:
            orders = Order.query.filter_by(table_id=table.table_id).all()

        # 상태별 금액 합계 계산
        total_amount_by_status = {
            "결제대기": 0,
            "결제확인": 0,
            "완료": 0
        }

        for order in orders:
            if order.order_status in total_amount_by_status:
                total_amount_by_status[order.order_status] += int(order.total_amount)

        total_sum = sum(total_amount_by_status.values())

        # 테이블 상태가 True일 때만 최신 주문 정보 포함
        if not last_reset_time and orders:
            latest_order = max(orders, key=lambda o: o.created_at)
            result.append({
                "table_id": table.table_id,
                "is_occupied": table.is_occupied,
                "latest_order_status": latest_order.order_status,
                "latest_order_time": latest_order.created_at.strftime("%Y-%m-%d %H:%M"),
                "total_amount_sum": total_sum
            })
        else:
            result.append({
                "table_id": table.table_id,
                "is_occupied": table.is_occupied,
                "total_amount_sum": total_sum
            })

    return jsonify(result)


# 특정 테이블 주문 내역 조회
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
                "menu_account": d.menu.price,
                "quantity": d.quantity,
                "is_served": d.is_served
            } for d in details
        ]
        result.append({
            "order_id": order.order_id,
            "depositor_name": order.depositor_name,
            "order_status": order.order_status,
            "total_amount": int(order.total_amount),
            "order_time": order.order_time.strftime("%Y-%m-%d %H:%M:%S"),
            "details": detail_data
        })

    return jsonify({
        "table_id": table_id,
        "orders": result
    })


# 결제 확인 처리
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


# 수동 주문 등록 (캐셔용)
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
        unit_price = int(menu.price)
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


# 주문 수정 (항목 수량 변경, 메뉴 변경 등)
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
        unit_price = int(menu.price)
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

    # 주문 존재 여부 확인
    order = Order.query.get(order_id)
    if not order:
        return jsonify({"error": "해당 주문이 존재하지 않습니다."}), 404

    # 이미 취소된 주문인지 확인
    if order.order_status == "취소":
        return jsonify({"message": "이미 취소된 주문입니다."}), 400

    # 주문 상세 항목 불러오기
    order_details = OrderDetail.query.filter_by(order_id=order_id).all()

    # stock 복구 부분
    for detail in order_details:
        menu = Menu.query.get(detail.menu_id)
        if menu:
            # 취소된 메뉴의 수량만큼 재고 증가
            menu.stock_quantity += detail.quantity  

    # 주문 상태 변경
    order.order_status = "취소"
    db.session.commit()

    return jsonify({
        "message": "주문이 취소되었고, 재고가 복구되었습니다.",
        "order_id": order_id
    }), 200

@cashier_bp.route('/ordermanagement', methods=['GET'])
def get_all_orders():
    orders = Order.query.order_by(Order.created_at.desc()).all()
    result = []

    for order in orders:
        items = order.order_details
        summary = []
        for item in items[:2]:
            summary.append(f"{item.menu.menu_name}({item.quantity}개)")
        if len(items) > 2:
            summary.append(f"외 {len(items) - 2}개")

        result.append({
            "order_id": order.order_id,
            "table_id": order.table_id,
            "depositor_name": order.depositor_name,
            "total_amount": int(order.total_amount),
            "order_status": order.order_status,
            "order_time": order.order_time.strftime("%Y-%m-%d %H:%M:%S"),
            "menu_summary": " ".join(summary)
        })

    return jsonify({"orders": result})
#테이블 주문에 대한 상태를 수정하는 부분인데 어떻게 작동하는겨?
#
@cashier_bp.route('/orders/<int:order_id>/status', methods=['PATCH'])
def update_order_status(order_id):
    data = request.get_json()
    new_status = data.get('order_status')

    if new_status not in ['결제대기', '결제확인', '완료', '취소']:
        return jsonify({"error": "유효하지 않은 상태입니다."}), 400

    order = Order.query.get(order_id)
    if not order:
        return jsonify({"error": "주문이 존재하지 않습니다."}), 404

    order.order_status = new_status
    db.session.commit()

    return jsonify({
        "success": True,
        "order_id": order_id,
        "order_status": new_status,
        "message": "주문 상태가 변경되었습니다."
    })


@cashier_bp.route('/tables/reset', methods=['POST'])
def reset_table():
    data = request.get_json()
    table_id = data.get("table_id")

    table = StoreTable.query.get(table_id)
    if not table:
        return jsonify({"error": "테이블을 찾을 수 없습니다."}), 404

    table.is_occupied = False
    db.session.commit()

    return jsonify({
        "success": True,
        "message": f"테이블 {table_id}번이 정리되었습니다."
    })