from flask import Blueprint, render_template, request, redirect, url_for, flash
from items import items
from auth_decorators import login_required, staff_required

product_bp = Blueprint('admin_product', __name__, url_prefix='/admin')


@product_bp.route('/products')
@login_required
@staff_required
def admin_products():
    return render_template('admin/products.html', products=items)


@product_bp.route('/products/add', methods=['GET', 'POST'])
@login_required
@staff_required
def add_product():
    global items
    if request.method == 'POST':
        title = request.form.get('title')
        price_val = request.form.get('price')
        category = request.form.get('category')
        image = request.form.get('image', '')

        if title and price_val and category:
            try:
                price = float(price_val)
            except ValueError:
                flash('Invalid price value.', 'danger')
                return redirect(url_for('admin_product.admin_products'))

            new_id = max([x['id'] for x in items]) + 1 if items else 1
            new_item = {
                "id": new_id,
                "title": title,
                "price": price,
                "description": "",
                "category": category,
                "image": image or "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=500",
                "rating": {
                    "rate": 0.0,
                    "count": 0
                }
            }
            items.append(new_item)
            flash(f'Product "{title}" added successfully!', 'success')
            return redirect(url_for('admin_product.admin_products'))
        else:
            flash('All fields are required.', 'danger')
            return redirect(url_for('admin_product.admin_products'))
    return render_template('admin/add_product.html')


@product_bp.route('/products/edit/<int:product_id>', methods=['GET', 'POST'])
@login_required
@staff_required
def edit_product(product_id):
    global items
    item = next((x for x in items if x['id'] == product_id), None)
    if not item:
        flash('Product not found.', 'danger')
        return redirect(url_for('admin_product.admin_products'))

    if request.method == 'POST':
        title = request.form.get('title')
        price_val = request.form.get('price')
        category = request.form.get('category')
        image = request.form.get('image', '')

        if title and price_val and category:
            try:
                price = float(price_val)
            except ValueError:
                flash('Invalid price value.', 'danger')
                return redirect(url_for('admin_product.edit_product', product_id=product_id))

            item['title'] = title
            item['price'] = price
            item['category'] = category
            if image:
                item['image'] = image
            flash(f'Product "{title}" updated successfully!', 'success')
            return redirect(url_for('admin_product.admin_products'))
        else:
            flash('All fields are required.', 'danger')
            return redirect(url_for('admin_product.edit_product', product_id=product_id))

    return render_template('admin/edit_product.html', item=item)


@product_bp.route('/products/delete/<int:product_id>', methods=['POST'])
@login_required
@staff_required
def delete_product(product_id):
    global items
    item = next((x for x in items if x['id'] == product_id), None)
    if item:
        items.remove(item)
        flash(f'Product "{item["title"]}" deleted successfully!', 'success')
    else:
        flash('Product not found.', 'danger')
    return redirect(url_for('admin_product.admin_products'))
