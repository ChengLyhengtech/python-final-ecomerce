import json
import requests
from flask import Flask, render_template, request, redirect, url_for, make_response, flash
from items import items

app = Flask(__name__)
app.secret_key = 'super_secret_heng_key'
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

@app.route('/')

@app.route('/contact')
def contact():
    return render_template('customer/contact.html')

@app.route('/login')
def login():
    return render_template('customer/share/login.html')

@app.route('/register')
def register():
    return render_template('customer/share/register.html')

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


# admin route

# Mock Data for Categories & Users
mock_categories = ["men's clothing", "jewelery", "electronics", "women's clothing"]
mock_users = [
    {"id": 1, "name": "John Doe", "email": "john@example.com", "role": "Admin"},
    {"id": 2, "name": "Jane Smith", "email": "jane@example.com", "role": "Editor"},
]

@app.route('/admin')
@app.route('/admin/dashboard')
def admin_dashboard():
    stats = {
        "total_products": len(items),
        "total_categories": len(mock_categories),
        "total_users": len(mock_users)
    }
    return render_template('admin/dashboard.html', stats=stats)

@app.route('/admin/products')
def admin_products():
    return render_template('admin/products.html', products=items)

@app.route('/admin/categories')
def admin_categories():
    return render_template('admin/categories.html', categories=mock_categories)

@app.route('/admin/users')
def admin_users():
    return render_template('admin/users.html', users=mock_users)

@app.route('/admin/products/add', methods=['GET', 'POST'])
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
                return redirect(url_for('admin_products'))
            
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
            return redirect(url_for('admin_products'))
        else:
            flash('All fields are required.', 'danger')
            return redirect(url_for('admin_products'))
    return render_template('admin/add_product.html')

@app.route('/admin/products/edit/<int:product_id>', methods=['GET', 'POST'])
def edit_product(product_id):
    global items
    item = next((x for x in items if x['id'] == product_id), None)
    if not item:
        flash('Product not found.', 'danger')
        return redirect(url_for('admin_products'))
        
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
                return redirect(url_for('edit_product', product_id=product_id))
            
            item['title'] = title
            item['price'] = price
            item['category'] = category
            if image:
                item['image'] = image
            flash(f'Product "{title}" updated successfully!', 'success')
            return redirect(url_for('admin_products'))
        else:
            flash('All fields are required.', 'danger')
            return redirect(url_for('edit_product', product_id=product_id))
            
    return render_template('admin/edit_product.html', item=item)

@app.route('/admin/products/delete/<int:product_id>', methods=['POST'])
def delete_product(product_id):
    global items
    item = next((x for x in items if x['id'] == product_id), None)
    if item:
        items.remove(item)
        flash(f'Product "{item["title"]}" deleted successfully!', 'success')
    else:
        flash('Product not found.', 'danger')
    return redirect(url_for('admin_products'))

@app.route('/admin/categories/add', methods=['GET', 'POST'])
def add_category():
    global mock_categories
    if request.method == 'POST':
        category_name = request.form.get('category_name')
        if category_name:
            mock_categories.append(category_name)
            flash(f'Category "{category_name}" added successfully!', 'success')
            return redirect(url_for('admin_categories'))
        else:
            flash('Category name is required.', 'danger')
            return redirect(url_for('admin_categories'))
    return render_template('admin/add_category.html')

@app.route('/admin/categories/edit/<int:category_id>', methods=['GET', 'POST'])
def edit_category(category_id):
    global mock_categories
    if category_id - 1 >= len(mock_categories) or category_id - 1 < 0:
        flash('Category not found.', 'danger')
        return redirect(url_for('admin_categories'))
        
    if request.method == 'POST':
        category_name = request.form.get('category_name')
        if category_name:
            old_name = mock_categories[category_id - 1]
            mock_categories[category_id - 1] = category_name
            flash(f'Category changed from "{old_name}" to "{category_name}"!', 'success')
            return redirect(url_for('admin_categories'))
        else:
            flash('Category name is required.', 'danger')
            return redirect(url_for('edit_category', category_id=category_id))
            
    category_name = mock_categories[category_id - 1]
    return render_template('admin/edit_category.html', category=category_name)

@app.route('/admin/categories/delete/<int:category_id>', methods=['POST'])
def delete_category(category_id):
    global mock_categories
    if 0 < category_id <= len(mock_categories):
        deleted_name = mock_categories.pop(category_id - 1)
        flash(f'Category "{deleted_name}" deleted successfully!', 'success')
    else:
        flash('Category not found.', 'danger')
    return redirect(url_for('admin_categories'))

# --- USERS CRUD ---
@app.route('/admin/users/add', methods=['GET', 'POST'])
def add_user():
    global mock_users
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        role = request.form.get('role')
        if name and email and role:
            new_id = max([x['id'] for x in mock_users]) + 1 if mock_users else 1
            new_user = {
                "id": new_id,
                "name": name,
                "email": email,
                "role": role
            }
            mock_users.append(new_user)
            flash(f'User "{name}" added successfully!', 'success')
            return redirect(url_for('admin_users'))
        else:
            flash('All fields are required.', 'danger')
            return redirect(url_for('admin_users'))
    return render_template('admin/add_user.html')

@app.route('/admin/users/edit/<int:user_id>', methods=['GET', 'POST'])
def edit_user(user_id):
    global mock_users
    user = next((x for x in mock_users if x['id'] == user_id), None)
    if not user:
        flash('User not found.', 'danger')
        return redirect(url_for('admin_users'))
        
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        role = request.form.get('role')
        if name and email and role:
            user['name'] = name
            user['email'] = email
            user['role'] = role
            flash(f'User "{name}" updated successfully!', 'success')
            return redirect(url_for('admin_users'))
        else:
            flash('All fields are required.', 'danger')
            return redirect(url_for('edit_user', user_id=user_id))
            
    return render_template('admin/edit_user.html', user=user)

@app.route('/admin/users/delete/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    global mock_users
    user = next((x for x in mock_users if x['id'] == user_id), None)
    if user:
        mock_users.remove(user)
        flash(f'User "{user["name"]}" deleted successfully!', 'success')
    else:
        flash('User not found.', 'danger')
    return redirect(url_for('admin_users'))

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