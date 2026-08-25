from flask import Blueprint, render_template, request, redirect, url_for, flash
from auth_decorators import login_required, staff_required

category_bp = Blueprint('admin_category', __name__, url_prefix='/admin')

mock_categories = ["men's clothing", "jewelery", "electronics", "women's clothing"]


@category_bp.route('/categories')
@login_required
@staff_required
def admin_categories():
    return render_template('admin/categories.html', categories=mock_categories)


@category_bp.route('/categories/add', methods=['GET', 'POST'])
@login_required
@staff_required
def add_category():
    global mock_categories
    if request.method == 'POST':
        category_name = request.form.get('category_name')
        if category_name:
            mock_categories.append(category_name)
            flash(f'Category "{category_name}" added successfully!', 'success')
            return redirect(url_for('admin_category.admin_categories'))
        else:
            flash('Category name is required.', 'danger')
            return redirect(url_for('admin_category.admin_categories'))
    return render_template('admin/add_category.html')


@category_bp.route('/categories/edit/<int:category_id>', methods=['GET', 'POST'])
@login_required
@staff_required
def edit_category(category_id):
    global mock_categories
    if category_id - 1 >= len(mock_categories) or category_id - 1 < 0:
        flash('Category not found.', 'danger')
        return redirect(url_for('admin_category.admin_categories'))

    if request.method == 'POST':
        category_name = request.form.get('category_name')
        if category_name:
            old_name = mock_categories[category_id - 1]
            mock_categories[category_id - 1] = category_name
            flash(f'Category changed from "{old_name}" to "{category_name}"!', 'success')
            return redirect(url_for('admin_category.admin_categories'))
        else:
            flash('Category name is required.', 'danger')
            return redirect(url_for('admin_category.edit_category', category_id=category_id))

    category_name = mock_categories[category_id - 1]
    return render_template('admin/edit_category.html', category=category_name)


@category_bp.route('/categories/delete/<int:category_id>', methods=['POST'])
@login_required
@staff_required
def delete_category(category_id):
    global mock_categories
    if 0 < category_id <= len(mock_categories):
        deleted_name = mock_categories.pop(category_id - 1)
        flash(f'Category "{deleted_name}" deleted successfully!', 'success')
    else:
        flash('Category not found.', 'danger')
    return redirect(url_for('admin_category.admin_categories'))
