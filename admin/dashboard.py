from flask import Blueprint, render_template
from models import User, Product, Category
from auth_decorators import login_required, staff_required

dashboard_bp = Blueprint('admin_dashboard', __name__, url_prefix='/admin')


@dashboard_bp.route('')
@dashboard_bp.route('/')
@dashboard_bp.route('/dashboard')
@login_required
@staff_required
def admin_dashboard():
    stats = {
        "total_products": Product.query.count(),
        "total_categories": Category.query.count(),
        "total_users": User.query.count()
    }
    return render_template('admin/dashboard.html', stats=stats)

