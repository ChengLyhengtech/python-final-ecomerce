import json
import requests
from flask import Flask, render_template, request, redirect, url_for, make_response
from items import items

app = Flask(__name__)
# --- TELEGRAM BOT CONFIGURATION ---
BOT_TOKEN = "8712622989:AAGcjjd6Gb7r9q7yeoRkPFvMiZaDOwHZRJ4"
TELEGRAM_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
CHAT_ID = "@ssbong_group"
@app.route('/')
def home():
    # This looks for index.html inside the 'templates' folder
    return render_template('customer/index.html',item=items)

@app.route('/product')
def products():
    return render_template('customer/products.html',item=items)

@app.route('/contact')
def contact():
    return render_template('customer/contact.html')

@app.route('/login')
def login():
    return render_template('share/login.html')

@app.route('/register')
def register():
    return render_template('share/register.html')

@app.route('/favorites')
def favorites():
    return render_template('customer/wishlist.html')

@app.route('/about')
def about():
    return render_template('customer/about.html')


@app.route('/view_product/<int:item_id>')
def view_product(item_id):
    # 1. Find the current product
    current_item = next((item for item in items if item['id'] == item_id), None)

    if not current_item:
        return "Product not found 404"

    # 2. Filter for related products (same category, exclude current product)
    related_products = [
        item for item in items
        if item['category'] == current_item['category'] and item['id'] != item_id
    ]



    # Pass both variables to the template
    return render_template(
        'customer/view_product.html',
        item=current_item,
        related_products=related_products
    )

# --- NEW: ADD TO CART ROUTE ---
@app.route('/add_to_cart/<int:item_id>', methods=['POST'])
def add_to_cart(item_id):
    # 1. Get the existing cart from cookies, or create an empty dict if it doesn't exist
    cart_cookie = request.cookies.get('cart')
    cart = json.loads(cart_cookie) if cart_cookie else {}

    # 2. Update the quantity of the item
    str_item_id = str(item_id)
    if str_item_id in cart:
        cart[str_item_id] += 1
    else:
        cart[str_item_id] = 1

    # 3. Redirect to the cart page and save the updated cart in the cookie
    response = make_response(redirect(url_for('cart')))
    response.set_cookie('cart', json.dumps(cart), max_age=60 * 60 * 24 * 7)  # Lasts for 7 days

    # --- THE FIX ---
    return response

# --- UPDATED: CART ROUTE ---
@app.route('/cart')
def cart():
    # 1. Get the cart cookie
    cart_cookie = request.cookies.get('cart')
    cart = json.loads(cart_cookie) if cart_cookie else {}

    cart_items = []
    total_price = 0

    # 2. Match cookie item IDs with actual product details
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


# --- NEW: INCREASE QUANTITY ROUTE ---
@app.route('/increase_cart/<int:item_id>', methods=['POST'])
def increase_cart(item_id):
    cart_cookie = request.cookies.get('cart')
    cart = json.loads(cart_cookie) if cart_cookie else {}

    str_item_id = str(item_id)
    if str_item_id in cart:
        cart[str_item_id] += 1  # Add 1 to quantity

    response = make_response(redirect(url_for('cart')))
    response.set_cookie('cart', json.dumps(cart), max_age=60 * 60 * 24 * 7)
    return response


# --- NEW: DECREASE QUANTITY ROUTE ---
@app.route('/decrease_cart/<int:item_id>', methods=['POST'])
def decrease_cart(item_id):
    cart_cookie = request.cookies.get('cart')
    cart = json.loads(cart_cookie) if cart_cookie else {}

    str_item_id = str(item_id)
    if str_item_id in cart:
        if cart[str_item_id] > 1:
            cart[str_item_id] -= 1  # Reduce by 1 if greater than 1
        else:
            cart.pop(str_item_id)  # Remove entirely if quantity drops below 1

    response = make_response(redirect(url_for('cart')))
    response.set_cookie('cart', json.dumps(cart), max_age=60 * 60 * 24 * 7)
    return response


# --- NEW: REMOVE SINGLE PRODUCT ROUTE ---
@app.route('/remove_from_cart/<int:item_id>', methods=['POST'])
def remove_from_cart(item_id):
    cart_cookie = request.cookies.get('cart')
    cart = json.loads(cart_cookie) if cart_cookie else {}

    str_item_id = str(item_id)
    if str_item_id in cart:
        cart.pop(str_item_id)  # Deletes this item key from the dictionary entirely

    response = make_response(redirect(url_for('cart')))
    response.set_cookie('cart', json.dumps(cart), max_age=60 * 60 * 24 * 7)
    return response

# --- BONUS: CLEAR CART ROUTE ---
@app.route('/clear_cart')
def clear_cart():
    response = make_response(redirect(url_for('cart')))
    response.delete_cookie('cart')
    return response


# --- NEW: CHECKOUT ROUTE ---
@app.route('/checkout')
def checkout():
    # 1. Read the cart from the cookie to calculate the final amount
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

    # If the cart is empty, don't let them checkout; redirect back to home
    if not cart_items:
        return redirect(url_for('cart'))

    return render_template(
        'customer/checkout.html',
        cart_items=cart_items,
        total_price=round(total_price, 2)
    )


# --- NEW: PLACE ORDER ROUTE (Clears cart after fake payment) ---
# --- UPDATED: PLACE ORDER ROUTE WITH TELEGRAM NOTIFICATION ---
@app.route('/place_order', methods=['POST'])
def place_order():
    # 1. Grab buyer details directly from the submitted HTML form fields
    buyer_name = request.form.get('buyer_name')
    buyer_phone = request.form.get('buyer_phone')
    buyer_email = request.form.get('buyer_email')
    buyer_address = request.form.get('buyer_address')
    order_notes = request.form.get('order_notes', 'N/A')

    # 2. Re-read the cart from cookies to build the items list for Telegram
    cart_cookie = request.cookies.get('cart')
    cart = json.loads(cart_cookie) if cart_cookie else {}

    cart_items = []
    total_price = 0
    first_product_image = "https://www.stubbleandco.com/cdn/shop/files/the-tote-bag-black-front.jpg"  # Default Fallback

    # Loop to compile items list text
    item_list_text = ""
    for item_id_str, quantity in cart.items():
        product = next((item for item in items if str(item['id']) == item_id_str), None)
        if product:
            item_total = product['price'] * quantity
            total_price += item_total

            # Keep track of the first product's image to use as the main Telegram photo
            if not item_list_text:
                first_product_image = product['image']

            item_list_text += f"📦 <b>{product['title'][:25]}...</b>\n"
            item_list_text += f"   └ Qty: {quantity} × ${product['price']:.2f} = <b>${item_total:.2f}</b>\n\n"

    # If the cart was empty somehow, stop here
    if not cart_items and total_price == 0:
        return redirect(url_for('cart'))

    # 3. Construct clean, professional HTML formatted Telegram text
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

    # 4. Fire payload to the Telegram Channel
    # Use text instead of photo + caption
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

    # 5. Clear their shopping cart cookie and send them back to safety with an alert
    response = make_response(
        '<script>alert("KHQR Payment Received! Order sent to our team."); window.location="/";</script>')
    response.delete_cookie('cart')
    return response


# --- GLOBAL CONTEXT PROCESSOR FOR CART COUNT ---
@app.context_processor
def inject_cart_count():
    # 1. Get the cart cookie from the browser
    cart_cookie = request.cookies.get('cart')
    cart = json.loads(cart_cookie) if cart_cookie else {}

    # 2. Calculate the total sum of all item quantities
    total_items_count = sum(cart.values())

    # 3. Return it as a global dictionary variable available in all templates
    return dict(cart_count=total_items_count)

if __name__ == '__main__':
    # Start the server with debugging enabled
    app.run(debug=False, port=5000)