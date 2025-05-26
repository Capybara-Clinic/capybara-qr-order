from flask import Blueprint, jsonify, request
from app.models import db, Menu, Category, Order, OrderDetail, StoreTable

menu_bp = Blueprint('menu', __name__, url_prefix='/menu')

@menu_bp.route('/<int:table_id>', methods=['GET'])
def get_menu_and_orders(table_id):
    table = StoreTable.query.get(table_id)
    if not table:
        return jsonify({"error": "해당 테이블이 존재하지 않습니다."}), 404

    # 메뉴 불러오기
    categories = Category.query.order_by(Category.display_order).all()
    category_data = []
    for category in categories:
        menus = Menu.query.filter_by(category_id=category.category_id, is_available=True).all()
        menu_list = [
            {
                "menu_id": menu.menu_id,
                "menu_name": menu.menu_name,
                "description": menu.description,
                "price": float(menu.price),
                "image_url": menu.image_url,
                "stock_quantity": menu.stock_quantity,
                "is_available": menu.is_available
            } for menu in menus
        ]
        category_data.append({
            "category_id": category.category_id,
            "category_name": category.category_name,
            "menus": menu_list
        })

    # 초기화 이후 주문만 필터링
    active_orders = Order.query.filter(
        Order.table_id == table_id,
        Order.order_status.in_(['결제대기', '결제확인']),
        # 초기화 이후 주문만
        # 테이블 상태가 업데이트 되기 전 까지만 가져올것임
        Order.created_at > table.updated_at  
    ).all()

    order_list = []
    for order in active_orders:
        details = OrderDetail.query.filter_by(order_id=order.order_id).all()
        detail_data = [
            {
                "order_detail_id": d.order_detail_id,
                "menu_name": d.menu.menu_name,
                "quantity": d.quantity,
                "is_served": d.is_served
            } for d in details
        ]
        order_list.append({
            "order_id": order.order_id,
            "depositor_name": order.depositor_name,
            "status": order.order_status,
            "details": detail_data
        })

    return jsonify({
        "table_id": table_id,
        "categories": category_data,
        "active_orders": order_list
    })


@menu_bp.route('/stocks', methods=['GET'])
def get_all_menu_stock():
    menus = Menu.query.all()
    result = [
        {
            "menu_id": m.menu_id,
            "menu_name": m.menu_name,
            "stock_quantity": m.stock_quantity,
            "is_available": m.is_available
        } for m in menus
    ]
    return jsonify(result)


@menu_bp.route('/stock/update', methods=['POST'])
def update_menu_stock():
    data = request.get_json()
    menu_id = data.get('menu_id')
    new_stock = data.get('stock_quantity')

    if menu_id is None or new_stock is None:
        return jsonify({"error": "필수 값 누락"}), 400

    menu = Menu.query.get(menu_id)
    if not menu:
        return jsonify({"error": "해당 메뉴가 존재하지 않습니다."}), 404

    menu.stock_quantity = int(new_stock)
    db.session.commit()

    return jsonify({"message": "재고가 수정되었습니다.", "menu_id": menu_id})


@menu_bp.route('/disable', methods=['POST'])
def disable_menu():
    data = request.get_json()
    menu_id = data.get('menu_id')

    if not menu_id:
        return jsonify({"error": "menu_id가 필요합니다."}), 400

    menu = Menu.query.get(menu_id)
    if not menu:
        return jsonify({"error": "해당 메뉴가 존재하지 않습니다."}), 404

    menu.is_available = False
    db.session.commit()

    return jsonify({"message": "메뉴가 품절 처리되었습니다.", "menu_id": menu_id})