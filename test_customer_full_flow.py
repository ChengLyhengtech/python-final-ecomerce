import json
import unittest
from app import app, db
from models import Product, Category, ProductImage, User

class CustomerFlowTestCase(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        self.client = app.test_client()

        with app.app_context():
            db.drop_all()
            db.create_all()

            user = User(
                username='test_shopper',
                email='shopper@test.com',
                phone_number='012345678',
                role='user'
            )
            user.set_password('pass123')
            db.session.add(user)
            db.session.commit()

            cat1 = Category(name='Audio', description='Audio equipment')
            cat2 = Category(name='Laptops', description='Portable PCs')
            db.session.add_all([cat1, cat2])
            db.session.commit()

            p1 = Product(
                title='Studio Wireless Pro Headphones',
                cost=100.0,
                price=199.99,
                stock=10,
                description='High-end noise cancelling headphones',
                user_id=user.id,
                category_id=cat1.id,
                thumbnail='headphones.jpg'
            )
            p2 = Product(
                title='Lenovo ThinkPad X1',
                cost=800.0,
                price=1299.00,
                stock=5,
                description='Ultrabook for business professionals',
                user_id=user.id,
                category_id=cat2.id,
                thumbnail='thinkpad.jpg'
            )
            db.session.add_all([p1, p2])
            db.session.commit()

            img1 = ProductImage(image_url='headphones_side.jpg', product_id=p1.id)
            img2 = ProductImage(image_url='headphones_box.jpg', product_id=p1.id)
            db.session.add_all([img1, img2])
            db.session.commit()

    def test_home_page(self):
        res = self.client.get('/')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Discover Next-Level Shopping', res.data)
        self.assertIn(b'Shop By Category', res.data)
        # Should contain categories from DB
        self.assertIn(b'Audio', res.data)
        self.assertIn(b'Studio Wireless Pro Headphones', res.data)

    def test_products_page_and_filtering(self):
        # All products
        res = self.client.get('/products')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'All Products', res.data)
        self.assertIn(b'Studio Wireless Pro Headphones', res.data)

        # Filter by Category (Audio = 1)
        res_cat = self.client.get('/products?category=1')
        self.assertEqual(res_cat.status_code, 200)
        self.assertIn(b'Audio', res_cat.data)

        # Search filter
        res_search = self.client.get('/products?q=Lenovo')
        self.assertEqual(res_search.status_code, 200)
        self.assertIn(b'Lenovo', res_search.data)

        # Price sorting
        res_sort = self.client.get('/products?sort=price_asc')
        self.assertEqual(res_sort.status_code, 200)

    def test_view_product_and_gallery(self):
        with app.app_context():
            prod = Product.query.first()
            prod_id = prod.id

        res = self.client.get(f'/view_product/{prod_id}')
        self.assertEqual(res.status_code, 200)
        self.assertIn(prod.title.encode('utf-8'), res.data)
        self.assertIn(b'switchMainImage', res.data)
        self.assertIn(b'Add to Cart', res.data)

    def test_wishlist_toggle_and_view(self):
        with app.app_context():
            prod = Product.query.first()
            prod_id = prod.id

        # Toggle product into wishlist
        res = self.client.post(f'/wishlist/toggle/{prod_id}', follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'added to your wishlist', res.data)

        # Check wishlist page
        res_wl = self.client.get('/wishlist')
        self.assertEqual(res_wl.status_code, 200)
        self.assertIn(prod.title.encode('utf-8'), res_wl.data)

        # Remove from wishlist
        res_rem = self.client.post(f'/wishlist/remove/{prod_id}', follow_redirects=True)
        self.assertEqual(res_rem.status_code, 200)
        self.assertIn(b'Your Wishlist is Empty', res_rem.data)

    def test_cart_operations(self):
        with app.app_context():
            prod = Product.query.first()
            prod_id = prod.id

        # Add to cart
        res = self.client.post(f'/add_to_cart/{prod_id}', data={'quantity': 2}, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        # View cart
        res_cart = self.client.get('/cart')
        self.assertEqual(res_cart.status_code, 200)
        self.assertIn(prod.title.encode('utf-8'), res_cart.data)
        self.assertIn(b'Select All Products', res_cart.data)

        # Increase cart
        res_inc = self.client.post(f'/increase_cart/{prod_id}', follow_redirects=True)
        self.assertEqual(res_inc.status_code, 200)

        # Decrease cart
        res_dec = self.client.post(f'/decrease_cart/{prod_id}', follow_redirects=True)
        self.assertEqual(res_dec.status_code, 200)

    def test_checkout_selective_and_place_order(self):
        with app.app_context():
            prods = Product.query.all()
            p1 = prods[0]
            p2 = prods[1]
            p1_initial_stock = p1.stock
            p2_initial_stock = p2.stock

        # Add both to cart and consume flash messages
        self.client.post(f'/add_to_cart/{p1.id}', data={'quantity': 1}, follow_redirects=True)
        self.client.post(f'/add_to_cart/{p2.id}', data={'quantity': 2}, follow_redirects=True)

        # Checkout ONLY p1 (Selective Checkout!)
        res_checkout = self.client.post('/checkout', data={
            'selected_items': [str(p1.id)]
        })
        self.assertEqual(res_checkout.status_code, 200)
        self.assertIn(p1.title.encode('utf-8'), res_checkout.data)
        # p2 should NOT be in the checkout list
        self.assertNotIn(p2.title.encode('utf-8'), res_checkout.data)

        # Place Order for p1 only
        res_order = self.client.post('/place_order', data={
            'selected_items': [str(p1.id)],
            'buyer_name': 'Test Buyer',
            'buyer_phone': '012345678',
            'buyer_email': 'buyer@test.com',
            'buyer_address': 'Phnom Penh St 2002',
            'order_notes': 'Please call before arrival'
        }, follow_redirects=True)
        self.assertEqual(res_order.status_code, 200)
        self.assertIn(b'Order successfully placed', res_order.data)

        # Verify in cart that p1 was removed, and p2 REMAINS in the cart!
        res_cart = self.client.get('/cart')
        self.assertNotIn(p1.title.encode('utf-8'), res_cart.data)
        self.assertIn(p2.title.encode('utf-8'), res_cart.data)

        # Check DB stock
        with app.app_context():
            p1_refreshed = Product.query.get(p1.id)
            p2_refreshed = Product.query.get(p2.id)
            self.assertEqual(p1_refreshed.stock, p1_initial_stock - 1)
            self.assertEqual(p2_refreshed.stock, p2_initial_stock)

if __name__ == '__main__':
    unittest.main()
