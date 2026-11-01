import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from sqlalchemy import text
from auth_decorators import login_required, staff_required
from models import db, Category, Product
from upload_config import save_uploaded_file

category_bp = Blueprint('admin_category', __name__, url_prefix='/admin')


@category_bp.route('/categories')
@login_required
@staff_required
def admin_categories():
    # GET method using Raw SQL
    query = text("""
        SELECT c.id, c.name, c.image, c.description, COUNT(p.id) AS product_count
        FROM categories c
        LEFT JOIN products p ON c.id = p.category_id
        GROUP BY c.id, c.name, c.image, c.description
        ORDER BY c.id ASC
    """)
    result = db.session.execute(query)
    categories = result.mappings().all()
    return render_template('admin/categories.html', categories=categories)


@category_bp.route('/categories/add', methods=['GET', 'POST'])
@login_required
@staff_required
def add_category():
    if request.method == 'POST':
        category_name = request.form.get('category_name', '').strip()
        description = request.form.get('description', '').strip()

        if not category_name:
            flash('Category name is required.', 'danger')
            return redirect(url_for('admin_category.add_category'))

        # Check for existing duplicate name
        existing = Category.query.filter(Category.name.ilike(category_name)).first()
        if existing:
            flash(f'Category "{category_name}" already exists.', 'warning')
            return redirect(url_for('admin_category.add_category'))

        upload_folder = current_app.config.get('UPLOAD_FOLDER')

        try:
            image_file = request.files.get('image')
            image_filename = save_uploaded_file(image_file, upload_folder=upload_folder)

            new_cat = Category(
                name=category_name,
                image=image_filename,
                description=description or ''
            )
            db.session.add(new_cat)
            db.session.commit()
            flash(f'Category "{category_name}" created successfully!', 'success')
            return redirect(url_for('admin_category.admin_categories'))
        except ValueError as val_err:
            db.session.rollback()
            flash(str(val_err), 'danger')
            return redirect(url_for('admin_category.add_category'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating category: {str(e)}', 'danger')
            return redirect(url_for('admin_category.add_category'))

    return render_template('admin/add_category.html')


@category_bp.route('/categories/edit/<int:category_id>', methods=['GET', 'POST'])
@login_required
@staff_required
def edit_category(category_id):
    if request.method == 'POST':
        cat_obj = Category.query.get_or_404(category_id)
        category_name = request.form.get('category_name', '').strip()
        description = request.form.get('description', '').strip()

        if not category_name:
            flash('Category name is required.', 'danger')
            return redirect(url_for('admin_category.edit_category', category_id=category_id))

        duplicate = Category.query.filter(Category.name.ilike(category_name), Category.id != category_id).first()
        if duplicate:
            flash(f'Category "{category_name}" already exists.', 'warning')
            return redirect(url_for('admin_category.edit_category', category_id=category_id))

        upload_folder = current_app.config.get('UPLOAD_FOLDER')

        try:
            image_file = request.files.get('image')
            new_image = save_uploaded_file(image_file, upload_folder=upload_folder)
            if new_image:
                cat_obj.image = new_image

            cat_obj.name = category_name
            cat_obj.description = description or ''
            db.session.commit()
            flash(f'Category "{category_name}" updated successfully!', 'success')
            return redirect(url_for('admin_category.admin_categories'))
        except ValueError as val_err:
            db.session.rollback()
            flash(str(val_err), 'danger')
            return redirect(url_for('admin_category.edit_category', category_id=category_id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating category: {str(e)}', 'danger')
            return redirect(url_for('admin_category.edit_category', category_id=category_id))

    # GET method using Raw SQL
    cat_query = text("SELECT id, name, image, description FROM categories WHERE id = :id")
    category = db.session.execute(cat_query, {"id": category_id}).mappings().first()
    if not category:
        flash('Category not found.', 'danger')
        return redirect(url_for('admin_category.admin_categories'))

    return render_template('admin/edit_category.html', category=category)


@category_bp.route('/categories/delete/<int:category_id>', methods=['POST'])
@login_required
@staff_required
def delete_category(category_id):
    category = Category.query.get_or_404(category_id)
    try:
        product_count = Product.query.filter_by(category_id=category_id).count()
        if product_count > 0:
            flash(f'Cannot delete category "{category.name}" because it is currently assigned to {product_count} product(s).', 'warning')
            return redirect(url_for('admin_category.admin_categories'))

        upload_folder = current_app.config.get('UPLOAD_FOLDER')
        if category.image and upload_folder:
            file_path = os.path.join(upload_folder, category.image)
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except OSError:
                    pass

        name = category.name
        db.session.delete(category)
        db.session.commit()
        flash(f'Category "{name}" deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting category: {str(e)}', 'danger')

    return redirect(url_for('admin_category.admin_categories'))


