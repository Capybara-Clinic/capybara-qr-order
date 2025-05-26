from flask import Flask
from app.models import db
from config import Config

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)

    # 블루프린트 임포트
    from app.routes.menu import menu_bp
    from app.routes.order import order_bp
    from app.routes.cashier import cashier_bp
    from app.routes.kitchen import kitchen_bp
    from app.routes.serving import serving_bp

    # 블루프린트 등록
    app.register_blueprint(menu_bp)
    app.register_blueprint(order_bp)
    app.register_blueprint(cashier_bp)
    app.register_blueprint(kitchen_bp)   # ✅ 누락되었던 부분 추가
    app.register_blueprint(serving_bp)

    return app