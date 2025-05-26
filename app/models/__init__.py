from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Category(db.Model):
    __tablename__ = 'categories'
    category_id = db.Column(db.Integer, primary_key=True)
    category_name = db.Column(db.String(50), nullable=False)
    display_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())


class Menu(db.Model):
    __tablename__ = 'menus'
    menu_id = db.Column(db.Integer, primary_key=True)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.category_id'), nullable=False)
    menu_name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(500))
    price = db.Column(db.Numeric(10, 2), nullable=False)
    image_url = db.Column(db.String(255))
    is_available = db.Column(db.Boolean, default=True)
    is_best_seller = db.Column(db.Boolean, default=False)
    stock_quantity = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())

    category = db.relationship('Category', backref='menus')


class StoreTable(db.Model):
    __tablename__ = 'store_tables'
    table_id = db.Column(db.Integer, primary_key=True)
    is_occupied = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())


class Order(db.Model):
    __tablename__ = 'orders'
    order_id = db.Column(db.Integer, primary_key=True)
    table_id = db.Column(db.Integer, db.ForeignKey('store_tables.table_id'))
    depositor_name = db.Column(db.String(50), nullable=False)
    total_amount = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    order_status = db.Column(db.Enum('결제대기', '결제확인', '완료', '취소'), default='결제대기')
    order_time = db.Column(db.DateTime, server_default=db.func.now())
    order_number = db.Column(db.String(10))
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())

    table = db.relationship('StoreTable', backref='orders')


class OrderDetail(db.Model):
    __tablename__ = 'order_details'
    order_detail_id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.order_id'), nullable=False)
    menu_id = db.Column(db.Integer, db.ForeignKey('menus.menu_id'), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    unit_price = db.Column(db.Numeric(10, 2), nullable=False)
    subtotal = db.Column(db.Numeric(10, 2), nullable=False)
    is_served = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    order = db.relationship('Order', backref='order_details')
    menu = db.relationship('Menu', backref='order_details')


class Payment(db.Model):
    __tablename__ = 'payments'
    payment_id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.order_id'), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    payment_status = db.Column(db.Enum('대기중', '완료', '환불', '취소'), default='대기중')
    is_verified = db.Column(db.Boolean, default=False)
    payment_method = db.Column(db.Enum('계좌이체', '기타'), default='계좌이체')
    check_time = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())

    order = db.relationship('Order', backref='payment')


class QRCode(db.Model):
    __tablename__ = 'qr_codes'
    qr_id = db.Column(db.Integer, primary_key=True)
    table_id = db.Column(db.Integer, db.ForeignKey('store_tables.table_id'), nullable=False)
    qr_code_url = db.Column(db.String(255), nullable=False)
    redirect_url = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())

    table = db.relationship('StoreTable', backref='qr_code')