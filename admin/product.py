import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from auth_decorators import login_required, staff_required, current_user
from sqlalchemy import text
from models import db, Product, Category, ProductImage
from upload_config import save_uploaded_file, save_multiple_uploaded_files

product_bp = Blueprint('admin_product', __name__, url_prefix='/admin')


@product_bp.route('/products')
@login_required
@staff_required
def admin_products():
    query = text("""
        SELECT p.id, p.title, p.thumbnail, p.cost, p.price, p.stock, p.description, 
               p.user_id, p.category_id, c.name AS category_name, u.username AS creator_name,
               (SELECT COUNT(pi.id) FROM product_images pi WHERE pi.product_id = p.id) AS image_count
        FROM products p
        LEFT JOIN categories c ON p.category_id = c.id
        LEFT JOIN users u ON p.user_id = u.id
        ORDER BY p.id DESC
    """)
    result = db.session.execute(query)
    items = result.mappings().all()
    return render_template('admin/products.html', products=items)


@product_bp.route('/products/<int:product_id>')
@login_required
@staff_required
def product_details(product_id):
    product = Product.query.get_or_404(product_id)
    return render_template('admin/product_detail.html', product=product)



@product_bp.route('/products/add', methods=['GET', 'POST'])
@login_required
@staff_required
def add_product():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        cost = request.form.get('cost', '0').strip()
        price = request.form.get('price', '').strip()
        stock = request.form.get('stock', '0').strip()
        category_id = request.form.get('category_id', '').strip()
        description = request.form.get('description', '').strip()

        # Validate required fields
        if not title or not price or not category_id:
            flash('Title, price, and category are required.', 'danger')
            return redirect(url_for('admin_product.add_product'))

        try:
            cost_val = float(cost) if cost else 0.0
            price_val = float(price)
            stock_val = int(stock) if stock else 0
            category_id_val = int(category_id)
        except ValueError:
            flash('Invalid numeric format for price, cost, or stock.', 'danger')
            return redirect(url_for('admin_product.add_product'))

        # Get current user ID (creator)
        user_id = getattr(current_user, 'id', None) or session.get('user_id')
        if not user_id:
            flash('Session expired. Please log in again.', 'warning')
            return redirect(url_for('auth.login'))

        upload_folder = current_app.config.get('UPLOAD_FOLDER')

        try:
            # 1. Handle Thumbnail File Upload
            thumbnail_file = request.files.get('thumbnail')
            thumbnail_filename = save_uploaded_file(thumbnail_file, upload_folder=upload_folder)

            # 2. Handle Multi-image Gallery Uploads
            gallery_files = request.files.getlist('images') + request.files.getlist('images[]')
            valid_gallery_files = [f for f in gallery_files if f and hasattr(f, 'filename') and f.filename and f.filename.strip()]
            saved_images = save_multiple_uploaded_files(valid_gallery_files, upload_folder=upload_folder)

            # If no thumbnail was uploaded but gallery images exist, set the first gallery image as thumbnail
            if not thumbnail_filename and saved_images:
                thumbnail_filename = saved_images[0]

            new_product = Product(
                title=title,
                cost=cost_val,
                price=price_val,
                stock=stock_val,
                description=description,
                thumbnail=thumbnail_filename,
                category_id=category_id_val,
                user_id=user_id
            )

            db.session.add(new_product)
            db.session.flush()  # Flush to populate new_product.id

            for img_name in saved_images:
                prod_img = ProductImage(image_url=img_name, product_id=new_product.id)
                db.session.add(prod_img)

            db.session.commit()

            flash(f'Product "{title}" created successfully with {len(saved_images)} gallery image(s)!', 'success')
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return {'success': True, 'redirect': url_for('admin_product.admin_products')}
            return redirect(url_for('admin_product.admin_products'))

        except ValueError as val_err:
            db.session.rollback()
            flash(str(val_err), 'danger')
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return {'success': False, 'message': str(val_err)}, 400
            return redirect(url_for('admin_product.add_product'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating product: {str(e)}', 'danger')
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return {'success': False, 'message': str(e)}, 500
            return redirect(url_for('admin_product.add_product'))


    # GET request: fetch categories using raw SQL
    cat_query = text("SELECT id, name FROM categories ORDER BY name ASC")
    categories = db.session.execute(cat_query).mappings().all()
    return render_template('admin/add_product.html', categories=categories)


@product_bp.route('/products/edit/<int:product_id>', methods=['GET', 'POST'])
@login_required
@staff_required
def edit_product(product_id):
    product = Product.query.get_or_404(product_id)

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        cost = request.form.get('cost', '0').strip()
        price_val = request.form.get('price', '').strip()
        stock = request.form.get('stock', '0').strip()
        category_id = request.form.get('category_id', '').strip()
        description = request.form.get('description', '').strip()

        if not title or not price_val or not category_id:
            flash('Title, price, and category are required.', 'danger')
            return redirect(url_for('admin_product.edit_product', product_id=product_id))

        upload_folder = current_app.config.get('UPLOAD_FOLDER')

        try:
            product.title = title
            product.cost = float(cost) if cost else 0.0
            product.price = float(price_val)
            product.stock = int(stock) if stock else 0
            product.category_id = int(category_id)
            product.description = description

            # Handle new thumbnail upload if provided
            thumbnail_file = request.files.get('thumbnail')
            new_thumbnail = save_uploaded_file(thumbnail_file, upload_folder=upload_folder)
            if new_thumbnail:
                product.thumbnail = new_thumbnail

            # Handle additional multi-image uploads
            gallery_files = request.files.getlist('images') + request.files.getlist('images[]')
            valid_gallery_files = [f for f in gallery_files if f and hasattr(f, 'filename') and f.filename and f.filename.strip()]
            saved_images = save_multiple_uploaded_files(valid_gallery_files, upload_folder=upload_folder)
            for img_name in saved_images:
                prod_img = ProductImage(image_url=img_name, product_id=product.id)
                db.session.add(prod_img)

            # If product has no thumbnail but gallery images were added, set first gallery image
            if not product.thumbnail and saved_images:
                product.thumbnail = saved_images[0]

            db.session.commit()
            flash(f'Product "{title}" updated successfully!', 'success')
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return {'success': True, 'redirect': url_for('admin_product.admin_products')}
            return redirect(url_for('admin_product.admin_products'))

        except ValueError as val_err:
            db.session.rollback()
            flash(str(val_err), 'danger')
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return {'success': False, 'message': str(val_err)}, 400
            return redirect(url_for('admin_product.edit_product', product_id=product_id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating product: {str(e)}', 'danger')
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return {'success': False, 'message': str(e)}, 500
            return redirect(url_for('admin_product.edit_product', product_id=product_id))


    # GET request: fetch categories for dropdown
    cat_query = text("SELECT id, name FROM categories ORDER BY name ASC")
    categories = db.session.execute(cat_query).mappings().all()
    return render_template('admin/edit_product.html', product=product, categories=categories)


@product_bp.route('/products/<int:product_id>/images/delete/<int:image_id>', methods=['POST'])
@login_required
@staff_required
def delete_product_image(product_id, image_id):
    img = ProductImage.query.filter_by(id=image_id, product_id=product_id).first_or_404()
    product = Product.query.get_or_404(product_id)
    try:
        image_url = img.image_url
        db.session.delete(img)
        db.session.flush()

        # If product thumbnail was using this image, update thumbnail to another gallery image or None
        if product.thumbnail == image_url:
            remaining_img = ProductImage.query.filter_by(product_id=product_id).first()
            product.thumbnail = remaining_img.image_url if remaining_img else None

        # Delete file from disk if not referenced by any other product or product_image
        upload_folder = current_app.config.get('UPLOAD_FOLDER')
        if image_url and upload_folder:
            other_img = ProductImage.query.filter_by(image_url=image_url).first()
            other_prod = Product.query.filter_by(thumbnail=image_url).first()
            if not other_img and not other_prod:
                file_path = os.path.join(upload_folder, image_url)
                if os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                    except OSError:
                        pass

        db.session.commit()
        flash('Gallery image removed.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error removing image: {str(e)}', 'danger')

    return redirect(url_for('admin_product.edit_product', product_id=product_id))


@product_bp.route('/products/delete/<int:product_id>', methods=['POST'])
@login_required
@staff_required
def delete_product(product_id):
    product = Product.query.get_or_404(product_id)

    try:
        title = product.title
        upload_folder = current_app.config.get('UPLOAD_FOLDER')

        # Clean up files from disk
        if product.thumbnail and upload_folder:
            thumb_path = os.path.join(upload_folder, product.thumbnail)
            if os.path.exists(thumb_path):
                try:
                    os.remove(thumb_path)
                except OSError:
                    pass

        for img in product.images:
            if img.image_url and upload_folder:
                img_path = os.path.join(upload_folder, img.image_url)
                if os.path.exists(img_path):
                    try:
                        os.remove(img_path)
                    except OSError:
                        pass

        db.session.delete(product)
        db.session.commit()
        flash(f'Product "{title}" deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting product: {str(e)}', 'danger')

    return redirect(url_for('admin_product.admin_products'))