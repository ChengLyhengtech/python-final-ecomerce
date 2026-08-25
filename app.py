import json
from flask import Flask, request
from flask_migrate import Migrate

from models import db, User
from upload_config import init_upload_config
from customer import customer_bp, auth_bp
from admin import dashboard_bp, product_bp, category_bp, user_bp

app = Flask(__name__)
app.secret_key = 'super_secret_heng_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize File Upload Configuration
init_upload_config(app)

# Initialize Database & Migrations
db.init_app(app)
migrate = Migrate(app, db)

# Register Blueprints
app.register_blueprint(customer_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(product_bp)
app.register_blueprint(category_bp)
app.register_blueprint(user_bp)


# --- GLOBAL CONTEXT PROCESSOR FOR CART COUNT & USER SESSION ---
@app.context_processor
def inject_global_data():
    cart_cookie = request.cookies.get('cart')
    cart = json.loads(cart_cookie) if cart_cookie else {}
    total_items_count = sum(cart.values())
    return dict(cart_count=total_items_count)


def init_db():
    with app.app_context():
        db.create_all()
        # Seed default admin if no users exist
        if not User.query.first():
            admin_user = User(
                username='admin',
                email='admin@store.com',
                phone_number='012345678',
                role='admin',
                profile_image='no-profile.png'
            )
            admin_user.set_password('admin123')
            db.session.add(admin_user)
            db.session.commit()
            print("Default admin created: admin@store.com / admin123 (username: admin)")


if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)