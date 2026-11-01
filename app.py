import json
from flask import Flask, request
from flask_migrate import Migrate

from extensions import limiter, csrf, cors
from models import db, User
from upload_config import init_upload_config
from customer import customer_bp, auth_bp
from admin import dashboard_bp, product_bp, category_bp, user_bp
from api import api_bp

app = Flask(__name__)

app.config['SECRET_KEY'] = 'super_secret_heng_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {"echo": True}
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize Limiter
limiter.init_app(app)
csrf.init_app(app)
cors.init_app(app)

# Initialize File Upload Configuration
init_upload_config(app)

# Initialize Database & Migrations
db.init_app(app)
migrate = Migrate(app, db)

# Register Blueprints
app.register_blueprint(customer_bp)
app.register_blueprint(api_bp)
csrf.exempt(api_bp)  # <-- Add this line right here!
app.register_blueprint(auth_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(product_bp)
app.register_blueprint(category_bp)
app.register_blueprint(user_bp)


# --- GLOBAL CONTEXT PROCESSOR & TEMPLATE FILTERS ---
@app.template_filter('media_url')
def media_url_filter(filename, default=''):
    if not filename:
        return default or '/static/admin/img/no-profile.png'
    if filename.startswith(('http://', 'https://', 'data:', '/static/', '/')):
        return filename
    return f"/static/admin/uploads/{filename}"


@app.context_processor
def inject_global_data():
    cart_cookie = request.cookies.get('cart')
    cart = {}
    if cart_cookie:
        try:
            cart = json.loads(cart_cookie)
            if not isinstance(cart, dict):
                cart = {}
        except Exception:
            cart = {}
    total_items_count = sum(cart.values()) if isinstance(cart, dict) else 0

    wishlist_cookie = request.cookies.get('wishlist')
    wishlist_ids = []
    if wishlist_cookie:
        try:
            wishlist_ids = json.loads(wishlist_cookie)
            if not isinstance(wishlist_ids, list):
                wishlist_ids = []
            wishlist_ids = [int(x) for x in wishlist_ids if str(x).isdigit()]
        except Exception:
            wishlist_ids = []

    return dict(
        cart_count=total_items_count,
        wishlist_count=len(wishlist_ids),
        wishlist_ids=wishlist_ids,
        media_url=media_url_filter
    )



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