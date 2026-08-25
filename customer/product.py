import json
import requests
from flask import Blueprint, render_template, request, redirect, url_for, make_response
from items import items
from auth_decorators import login_required

customer_bp = Blueprint('customer', __name__)

# --- TELEGRAM BOT CONFIGURATION ---
BOT_TOKEN = "8712622989:AAGcjjd6Gb7r9q7yeoRkPFvMiZaDOwHZRJ4"
TELEGRAM_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
CHAT_ID = "@ssbong_group"


@customer_bp.route('/')
def home():
    return render_template('customer/index.html', item=items)


@customer_bp.route('/product')
@customer_bp.route('/products')
def products():
    return render_template('customer/products.html', item=items)


@customer_bp.route('/contact')
def contact():
    return render_template('customer/contact.html')


@customer_bp.route('/favorites')
@login_required
def favorites():
    return render_template('customer/wishlist.html')


@customer_bp.route('/about')
def about():
    return render_template('customer/about.html')


@customer_bp.route('/view_product/<int:item_id>')
def view_product(item_id):
    current_item = next((item for item in items if item['id'] == item_id), None)

    if not current_item:
        return "Product not found 404", 404

    related_products = [
        item for item in items
        if item['category'] == current_item['category'] and item['id'] != item_id
    ]

    return render_template(
        'customer/view_product.html',
        item=current_item,
        related_products=related_products
    )


@customer_bp.route('/add_to_cart/<int:item_id>', methods=['POST'])
def add_to_cart(item_id):
    cart_cookie = request.cookies.get('cart')
    cart = json.loads(cart_cookie) if cart_cookie else {}

    str_item_id = str(item_id)
    if str_item_id in cart:
        cart[str_item_id] += 1
    else:
        cart[str_item_id] = 1

    response = make_response(redirect(url_for('customer.cart')))
    response.set_cookie('cart', json.dumps(cart), max_age=60 * 60 * 24 * 7)
    return response


@customer_bp.route('/cart')
def cart():
    cart_cookie = request.cookies.get('cart')
    cart = json.loads(cart_cookie) if cart_cookie else {}

    cart_items = []
    total_price = 0

    for item_id_str, quantity in cart.items():
        product = next((item for item in items if str(item['id']) == item_id_str), None)
        if product:
            item_total = product['price'] * quantity
            total_price += item_total
            cart_items.append({
                'product': product,
                'quantity': quantity,
                'item_total': round(item_total, 2)
            })

    return render_template(
        'customer/cart.html',
        cart_items=cart_items,
        total_price=round(total_price, 2)
    )


@customer_bp.route('/increase_cart/<int:item_id>', methods=['POST'])
def increase_cart(item_id):
    cart_cookie = request.cookies.get('cart')
    cart = json.loads(cart_cookie) if cart_cookie else {}

    str_item_id = str(item_id)
    if str_item_id in cart:
        cart[str_item_id] += 1

    response = make_response(redirect(url_for('customer.cart')))
    response.set_cookie('cart', json.dumps(cart), max_age=60 * 60 * 24 * 7)
    return response


@customer_bp.route('/decrease_cart/<int:item_id>', methods=['POST'])
def decrease_cart(item_id):
    cart_cookie = request.cookies.get('cart')
    cart = json.loads(cart_cookie) if cart_cookie else {}

    str_item_id = str(item_id)
    if str_item_id in cart:
        if cart[str_item_id] > 1:
            cart[str_item_id] -= 1
        else:
            cart.pop(str_item_id)

    response = make_response(redirect(url_for('customer.cart')))
    response.set_cookie('cart', json.dumps(cart), max_age=60 * 60 * 24 * 7)
    return response


@customer_bp.route('/remove_from_cart/<int:item_id>', methods=['POST'])
def remove_from_cart(item_id):
    cart_cookie = request.cookies.get('cart')
    cart = json.loads(cart_cookie) if cart_cookie else {}

    str_item_id = str(item_id)
    if str_item_id in cart:
        cart.pop(str_item_id)

    response = make_response(redirect(url_for('customer.cart')))
    response.set_cookie('cart', json.dumps(cart), max_age=60 * 60 * 24 * 7)
    return response


@customer_bp.route('/clear_cart')
def clear_cart():
    response = make_response(redirect(url_for('customer.cart')))
    response.delete_cookie('cart')
    return response


@customer_bp.route('/checkout')
def checkout():
    cart_cookie = request.cookies.get('cart')
    cart = json.loads(cart_cookie) if cart_cookie else {}

    cart_items = []
    total_price = 0

    for item_id_str, quantity in cart.items():
        product = next((item for item in items if str(item['id']) == item_id_str), None)
        if product:
            item_total = product['price'] * quantity
            total_price += item_total
            cart_items.append({
                'product': product,
                'quantity': quantity,
                'item_total': round(item_total, 2)
            })

    if not cart_items:
        return redirect(url_for('customer.cart'))

    return render_template(
        'customer/checkout.html',
        cart_items=cart_items,
        total_price=round(total_price, 2)
    )


@customer_bp.route('/place_order', methods=['POST'])
def place_order():
    buyer_name = request.form.get('buyer_name')
    buyer_phone = request.form.get('buyer_phone')
    buyer_email = request.form.get('buyer_email')
    buyer_address = request.form.get('buyer_address')
    order_notes = request.form.get('order_notes', 'N/A')

    cart_cookie = request.cookies.get('cart')
    cart = json.loads(cart_cookie) if cart_cookie else {}

    cart_items = []
    total_price = 0

    item_list_text = ""
    for item_id_str, quantity in cart.items():
        product = next((item for item in items if str(item['id']) == item_id_str), None)
        if product:
            item_total = product['price'] * quantity
            total_price += item_total
            item_list_text += f"📦 <b>{product['title'][:25]}...</b>\n"
            item_list_text += f"   └ Qty: {quantity} × ${product['price']:.2f} = <b>${item_total:.2f}</b>\n\n"

    if not cart_items and total_price == 0:
        return redirect(url_for('customer.cart'))

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
    telegram_text += f"💰 <b>TOTAL PAID (KHQR): ${total_price:.2f} USD</b>"

    payload = {
        "text": telegram_text,
        "parse_mode": "HTML",
        "chat_id": CHAT_ID
    }

    headers = {
        "accept": "application/json",
        "content-type": "application/json"
    }

    try:
        telegram_response = requests.post(TELEGRAM_URL, json=payload, headers=headers)
        print(f"Telegram Bot Status: {telegram_response.status_code}")
    except Exception as e:
        print(f"Failed to push notification to Telegram: {e}")

    response = make_response(
        '<script>alert("KHQR Payment Received! Order sent to our team."); window.location="/";</script>')
    response.delete_cookie('cart')
    return response
