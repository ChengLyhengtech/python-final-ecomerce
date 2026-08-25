from flask import Blueprint, render_template
from items import items
from models import User
from auth_decorators import login_required, staff_required
from .category import mock_categories

dashboard_bp = Blueprint('admin_dashboard', __name__, url_prefix='/admin')


@dashboard_bp.route('')
@dashboard_bp.route('/')
@dashboard_bp.route('/dashboard')
@login_required
@staff_required
def admin_dashboard():
    total_users_count = User.query.count()
    stats = {
        "total_products": len(items),
        "total_categories": len(mock_categories),
        "total_users": total_users_count
    }
    return render_template('admin/dashboard.html', stats=stats)
