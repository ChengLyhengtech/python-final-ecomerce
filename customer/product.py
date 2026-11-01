import json
import os
import requests
from decimal import Decimal
from dotenv import load_dotenv
from flask import (
    Blueprint, render_template, request, redirect, url_for,
    make_response, flash, session, jsonify
)
from models import db, Product, Category, ProductImage, User

customer_bp = Blueprint('customer', __name__)

# --- TELEGRAM BOT CONFIGURATION ---
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
TELEGRAM_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage" if BOT_TOKEN else None


# --- HELPER FUNCTIONS FOR CART & WISHLIST ---
def get_cart_from_cookie():
    cookie_val = request.cookies.get('cart')
    if not cookie_val:
        return {}
    try:
        cart = json.loads(cookie_val)
        if isinstance(cart, dict):
            # Ensure values are ints
            return {str(k): int(v) for k, v in cart.items() if int(v) > 0}
        return {}
    except Exception:
        return {}


def save_cart_to_response(response, cart_dict):
    if cart_dict:
        response.set_cookie('cart', json.dumps(cart_dict), max_age=60 * 60 * 24 * 7, samesite='Lax')
    else:
        response.delete_cookie('cart')
    return response


def get_wishlist_from_cookie():
    cookie_val = request.cookies.get('wishlist')
    if not cookie_val:
        return []
    try:
        wl = json.loads(cookie_val)
        if isinstance(wl, list):
            return [int(x) for x in wl if str(x).isdigit()]
        return []
    except Exception:
        return []


def save_wishlist_to_response(response, wishlist_list):
    # Keep unique IDs
    unique_ids = list(dict.fromkeys(wishlist_list))
    if unique_ids:
        response.set_cookie('wishlist', json.dumps(unique_ids), max_age=60 * 60 * 24 * 30, samesite='Lax')
    else:
        response.delete_cookie('wishlist')
    return response


# --- CUSTOMER VIEWS ---

@customer_bp.route('/')
def home():
    """Customer Homepage featuring dynamic categories and latest/featured products."""
    categories = Category.query.all()
    # Featured products: newest 8 products
    products = Product.query.order_by(Product.id.desc()).limit(8).all()
    return render_template('customer/index.html', products=products, categories=categories)


@customer_bp.route('/product')
@customer_bp.route('/products')
def products():
    """Shop page with category filtering, search, price range, and sorting."""
    category_id = request.args.get('category', type=int)
    search_query = request.args.get('q', '').strip()
    min_price = request.args.get('min_price', type=float)
    max_price = request.args.get('max_price', type=float)
    sort = request.args.get('sort', 'latest')

    query = Product.query

    # Category Filter
    if category_id:
        query = query.filter(Product.category_id == category_id)

    # Search Filter
    if search_query:
        search_filter = f"%{search_query}%"
        query = query.filter(
            Product.title.ilike(search_filter) | Product.description.ilike(search_filter)
        )

    # Price Filter
    if min_price is not None:
        query = query.filter(Product.price >= min_price)
    if max_price is not None:
        query = query.filter(Product.price <= max_price)

    # Sorting
    if sort == 'price_asc':
        query = query.order_by(Product.price.asc())
    elif sort == 'price_desc':
        query = query.order_by(Product.price.desc())
    elif sort == 'title_asc':
        query = query.order_by(Product.title.asc())
    else:
        query = query.order_by(Product.id.desc())

    all_products = query.all()
    categories = Category.query.all()

    return render_template(
        'customer/products.html',
        products=all_products,
        categories=categories,
        selected_category=category_id,
        search_query=search_query,
        min_price=min_price,
        max_price=max_price,
        sort=sort
    )


@customer_bp.route('/contact')
def contact():
    return render_template('customer/contact.html')


@customer_bp.route('/about')
def about():
    return render_template('customer/about.html')


@customer_bp.route('/view_product/<int:item_id>')
def view_product(item_id):
    """Product details page with multi-image gallery support and related products."""
    product = Product.query.get_or_404(item_id)

    # Collect all images (thumbnail + multi-image gallery from ProductImage)
    all_images = []
    if product.thumbnail:
        all_images.append(product.thumbnail)

    for img in product.images:
        if img.image_url and img.image_url not in all_images:
            all_images.append(img.image_url)

    # If no thumbnail or gallery image exists, provide fallback
    if not all_images:
        all_images.append('no-profile.png')

    # Fetch related products from the same category
    related_products = Product.query.filter(
        Product.category_id == product.category_id,
        Product.id != product.id
    ).limit(4).all()

    # If category has no other products, fetch latest products
    if not related_products:
        related_products = Product.query.filter(Product.id != product.id).order_by(Product.id.desc()).limit(4).all()

    wishlist_ids = get_wishlist_from_cookie()
    is_in_wishlist = product.id in wishlist_ids

    return render_template(
        'customer/view_product.html',
        item=product,
        product=product,
        all_images=all_images,
        related_products=related_products,
        is_in_wishlist=is_in_wishlist
    )


# --- WISHLIST MANAGEMENT ---

@customer_bp.route('/favorites', endpoint='favorites')
@customer_bp.route('/wishlist', endpoint='wishlist')
def wishlist():
    """Customer Wishlist page displaying favorited products."""
    wishlist_ids = get_wishlist_from_cookie()
    wishlist_products = []
    if wishlist_ids:
        # Preserve order or query matching products
        products = Product.query.filter(Product.id.in_(wishlist_ids)).all()
        # Create map for quick ordering
        product_map = {p.id: p for p in products}
        wishlist_products = [product_map[wid] for wid in wishlist_ids if wid in product_map]

    return render_template('customer/wishlist.html', products=wishlist_products)


@customer_bp.route('/favorites/toggle/<int:item_id>', endpoint='toggle_favorites', methods=['GET', 'POST'])
@customer_bp.route('/wishlist/toggle/<int:item_id>', endpoint='toggle_wishlist', methods=['GET', 'POST'])
def toggle_wishlist(item_id):
    """Toggle item in/out of customer wishlist (supports AJAX & regular redirects)."""
    product = Product.query.get_or_404(item_id)
    wishlist_ids = get_wishlist_from_cookie()

    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json

    if item_id in wishlist_ids:
        wishlist_ids.remove(item_id)
        in_wishlist = False
        message = f'"{product.title}" removed from your wishlist.'
    else:
        wishlist_ids.append(item_id)
        in_wishlist = True
        message = f'"{product.title}" added to your wishlist!'

    if is_ajax:
        resp = make_response(jsonify({
            'success': True,
            'in_wishlist': in_wishlist,
            'wishlist_count': len(wishlist_ids),
            'message': message
        }))
        return save_wishlist_to_response(resp, wishlist_ids)

    flash(message, 'success' if in_wishlist else 'info')
    redirect_target = request.referrer or url_for('customer.wishlist')
    resp = make_response(redirect(redirect_target))
    return save_wishlist_to_response(resp, wishlist_ids)


@customer_bp.route('/favorites/remove/<int:item_id>', endpoint='remove_from_favorites', methods=['GET', 'POST'])
@customer_bp.route('/wishlist/remove/<int:item_id>', endpoint='remove_from_wishlist', methods=['GET', 'POST'])
def remove_from_wishlist(item_id):
    wishlist_ids = get_wishlist_from_cookie()
    if item_id in wishlist_ids:
        wishlist_ids.remove(item_id)
        flash('Item removed from wishlist.', 'info')

    redirect_target = request.referrer or url_for('customer.wishlist')
    resp = make_response(redirect(redirect_target))
    return save_wishlist_to_response(resp, wishlist_ids)


@customer_bp.route('/favorites/clear', endpoint='clear_favorites', methods=['GET', 'POST'])
@customer_bp.route('/wishlist/clear', endpoint='clear_wishlist', methods=['GET', 'POST'])
def clear_wishlist():
    flash('Wishlist cleared.', 'info')
    resp = make_response(redirect(url_for('customer.wishlist')))
    return save_wishlist_to_response(resp, [])


# --- SHOPPING CART MANAGEMENT ---

@customer_bp.route('/cart')
def cart():
    """Customer Shopping Cart with live selection for checkout."""
    cart_dict = get_cart_from_cookie()
    cart_items = []
    total_price = Decimal('0.00')

    if cart_dict:
        product_ids = [int(pid) for pid in cart_dict.keys() if str(pid).isdigit()]
        products = Product.query.filter(Product.id.in_(product_ids)).all()
        prod_map = {p.id: p for p in products}

        for pid in product_ids:
            product = prod_map.get(pid)
            if product:
                quantity = cart_dict.get(str(pid), 1)
                item_price = Decimal(str(product.price))
                item_total = item_price * quantity
                total_price += item_total
                cart_items.append({
                    'product': product,
                    'quantity': quantity,
                    'item_total': float(item_total),
                    'in_stock': (product.stock >= quantity)
                })

    return render_template(
        'customer/cart.html',
        cart_items=cart_items,
        total_price=float(total_price)
    )


@customer_bp.route('/add_to_cart/<int:item_id>', methods=['POST'])
def add_to_cart(item_id):
    """Add a product to cart with chosen quantity."""
    product = Product.query.get_or_404(item_id)
    cart_dict = get_cart_from_cookie()

    try:
        qty_to_add = int(request.form.get('quantity', 1))
        if qty_to_add < 1:
            qty_to_add = 1
    except (ValueError, TypeError):
        qty_to_add = 1

    str_id = str(item_id)
    current_qty = cart_dict.get(str_id, 0)
    new_qty = current_qty + qty_to_add

    # Check stock
    if product.stock <= 0:
        flash(f'Sorry, "{product.title}" is currently out of stock.', 'warning')
        return redirect(request.referrer or url_for('customer.view_product', item_id=item_id))

    if new_qty > product.stock:
        new_qty = product.stock
        flash(f'Limited to available stock ({product.stock} items) for "{product.title}".', 'info')

    cart_dict[str_id] = new_qty

    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json
    if is_ajax:
        total_count = sum(cart_dict.values())
        resp = make_response(jsonify({
            'success': True,
            'message': f'"{product.title}" added to cart!',
            'cart_count': total_count
        }))
        return save_cart_to_response(resp, cart_dict)

    flash(f'Added {qty_to_add} × "{product.title}" to cart!', 'success')
    # If the user clicked "Add to cart" inside view_product, stay or go to cart
    next_url = request.form.get('next') or request.referrer or url_for('customer.cart')
    resp = make_response(redirect(next_url))
    return save_cart_to_response(resp, cart_dict)


@customer_bp.route('/increase_cart/<int:item_id>', methods=['POST'])
def increase_cart(item_id):
    cart_dict = get_cart_from_cookie()
    product = Product.query.get(item_id)
    str_id = str(item_id)

    if str_id in cart_dict:
        if product and cart_dict[str_id] >= product.stock:
            flash(f'Cannot add more. Available stock is {product.stock}.', 'warning')
        else:
            cart_dict[str_id] += 1

    resp = make_response(redirect(url_for('customer.cart')))
    return save_cart_to_response(resp, cart_dict)


@customer_bp.route('/decrease_cart/<int:item_id>', methods=['POST'])
def decrease_cart(item_id):
    cart_dict = get_cart_from_cookie()
    str_id = str(item_id)

    if str_id in cart_dict:
        if cart_dict[str_id] > 1:
            cart_dict[str_id] -= 1
        else:
            cart_dict.pop(str_id, None)

    resp = make_response(redirect(url_for('customer.cart')))
    return save_cart_to_response(resp, cart_dict)


@customer_bp.route('/remove_from_cart/<int:item_id>', methods=['POST'])
def remove_from_cart(item_id):
    cart_dict = get_cart_from_cookie()
    str_id = str(item_id)

    if str_id in cart_dict:
        cart_dict.pop(str_id, None)
        flash('Item removed from cart.', 'info')

    resp = make_response(redirect(url_for('customer.cart')))
    return save_cart_to_response(resp, cart_dict)


@customer_bp.route('/clear_cart', methods=['GET', 'POST'])
def clear_cart():
    flash('Cart emptied.', 'info')
    resp = make_response(redirect(url_for('customer.cart')))
    return save_cart_to_response(resp, {})


# --- CHECKOUT & ORDERING ---

@customer_bp.route('/checkout', methods=['GET', 'POST'])
def checkout():
    """
    Checkout page. Supports selecting all cart items or checking only specific products.
    Accepts selected item IDs via POST form or GET query param 'selected'.
    """
    cart_dict = get_cart_from_cookie()
    if not cart_dict:
        flash('Your cart is empty. Please add items before checking out.', 'warning')
        return redirect(url_for('customer.cart'))

    # Retrieve selected item IDs
    selected_ids = []
    if request.method == 'POST':
        # Selected items from cart form
        selected_ids = request.form.getlist('selected_items')
    else:
        # Check GET query params (e.g. ?selected=1,2 or repeated ?selected=1&selected=2)
        get_selected = request.args.getlist('selected')
        if not get_selected and request.args.get('selected'):
            get_selected = request.args.get('selected').split(',')
        selected_ids = [s.strip() for s in get_selected if s.strip()]

    # If no specific items selected, default to ALL items in cart
    if not selected_ids:
        selected_ids = list(cart_dict.keys())

    # Filter to only IDs that exist in the cart
    selected_ids = [str(x) for x in selected_ids if str(x) in cart_dict]

    if not selected_ids:
        flash('Please select at least one item from your cart to proceed with checkout.', 'warning')
        return redirect(url_for('customer.cart'))

    # Fetch product details for selected items
    int_ids = [int(x) for x in selected_ids if x.isdigit()]
    products = Product.query.filter(Product.id.in_(int_ids)).all()
    prod_map = {p.id: p for p in products}

    checkout_items = []
    total_price = Decimal('0.00')

    for pid in int_ids:
        product = prod_map.get(pid)
        if product:
            quantity = cart_dict.get(str(pid), 1)
            item_price = Decimal(str(product.price))
            item_total = item_price * quantity
            total_price += item_total
            checkout_items.append({
                'product': product,
                'quantity': quantity,
                'item_total': float(item_total),
                'in_stock': (product.stock >= quantity)
            })

    # Pre-fill user profile info if logged in
    current_user_obj = None
    user_id = session.get('user_id')
    if user_id:
        current_user_obj = User.query.get(user_id)

    return render_template(
        'customer/checkout.html',
        cart_items=checkout_items,
        selected_ids=selected_ids,
        total_price=float(total_price),
        user=current_user_obj
    )


@customer_bp.route('/place_order', methods=['POST'])
def place_order():
    """Processes order, updates product stock, sends Telegram notification, and removes purchased items."""
    buyer_name = request.form.get('buyer_name', '').strip()
    buyer_phone = request.form.get('buyer_phone', '').strip()
    buyer_email = request.form.get('buyer_email', '').strip()
    buyer_address = request.form.get('buyer_address', '').strip()
    order_notes = request.form.get('order_notes', 'N/A').strip() or 'N/A'

    # Get the specific items that were selected for this checkout
    selected_ids = request.form.getlist('selected_items')
    if not selected_ids:
        # If passed as comma-separated string
        raw_sel = request.form.get('selected_items_str', '')
        if raw_sel:
            selected_ids = [s.strip() for s in raw_sel.split(',') if s.strip()]

    cart_dict = get_cart_from_cookie()

    # If no selected items specified, checkout all items in cart
    if not selected_ids:
        selected_ids = list(cart_dict.keys())

    selected_ids = [str(x) for x in selected_ids if str(x) in cart_dict]

    if not selected_ids:
        flash('No valid items found to place an order.', 'danger')
        return redirect(url_for('customer.cart'))

    int_ids = [int(x) for x in selected_ids if x.isdigit()]
    products = Product.query.filter(Product.id.in_(int_ids)).all()
    prod_map = {p.id: p for p in products}

    ordered_items = []
    total_price = Decimal('0.00')
    item_list_text = ""

    for pid in int_ids:
        product = prod_map.get(pid)
        if product:
            quantity = cart_dict.get(str(pid), 1)
            item_price = Decimal(str(product.price))
            item_total = item_price * quantity
            total_price += item_total

            # Deduct stock in DB
            product.stock = max(0, product.stock - quantity)
            ordered_items.append((product, quantity, item_total))

            item_list_text += f"📦 <b>{product.title[:28]}</b>\n"
            item_list_text += f"   └ Qty: {quantity} × ${item_price:.2f} = <b>${item_total:.2f}</b>\n\n"

    # Commit stock updates
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"Error updating stock: {e}")

    # Build Telegram Notification
    if TELEGRAM_URL and CHAT_ID:
        telegram_text = f"<b>🔔 NEW KHQR ORDER RECEIVED</b>\n"
        telegram_text += f"<b>----------------------------------</b>\n\n"
        telegram_text += f"👤 <b>Customer:</b> {buyer_name}\n"
        telegram_text += f"📞 <b>Phone:</b> <code>{buyer_phone}</code>\n"
        telegram_text += f"📧 <b>Email:</b> <code>{buyer_email}</code>\n"
        telegram_text += f"📍 <b>Address:</b> {buyer_address}\n"
        telegram_text += f"📝 <b>Notes:</b> <i>{order_notes}</i>\n\n"
        telegram_text += f"<b>🛒 ORDER ITEMS:</b>\n"
        telegram_text += item_list_text
        telegram_text += f"<b>----------------------------------</b>\n"
        telegram_text += f"💰 <b>TOTAL PAID (KHQR): ${float(total_price):.2f} USD</b>"

        payload = {
            "text": telegram_text,
            "parse_mode": "HTML",
            "chat_id": CHAT_ID
        }

        try:
            requests.post(TELEGRAM_URL, json=payload, headers={"content-type": "application/json"}, timeout=5)
        except Exception as e:
            print(f"Failed to push notification to Telegram: {e}")

    # Remove ONLY the selected/checked-out items from the user's cart!
    for pid_str in selected_ids:
        cart_dict.pop(pid_str, None)

    flash(f"Order successfully placed for ${float(total_price):.2f}! Thank you for your purchase.", "success")
    response = make_response(redirect(url_for('customer.home')))
    return save_cart_to_response(response, cart_dict)
