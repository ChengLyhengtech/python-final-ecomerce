import io
import unittest
from app import app, db, User
from models import Product, Category, ProductImage
from extensions import limiter


class ProductAndCategoryCrudTestCase(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        app.config['RATELIMIT_ENABLED'] = False
        limiter.enabled = False
        self.client = app.test_client()

        with app.app_context():
            db.drop_all()
            db.create_all()

            # Create an admin user
            admin = User(
                username='admin_boss',
                email='admin_boss@store.com',
                phone_number='012345678',
                role='admin',
                profile_image='no-profile.png'
            )
            admin.set_password('admin123')
            db.session.add(admin)

            # Create a staff user
            staff = User(
                username='staff_member',
                email='staff@store.com',
                phone_number='098765432',
                role='staff',
                profile_image='no-profile.png'
            )
            staff.set_password('staff123')
            db.session.add(staff)

            db.session.commit()

    def test_category_file_upload_and_crud(self):
        # 1. Login as staff/admin
        self.client.post('/login', data={'username': 'staff_member', 'password': 'staff123'}, follow_redirects=True)

        # 2. Add Category with file upload
        fake_cat_image = (io.BytesIO(b'fake category image data'), 'electronics_icon.png')
        res = self.client.post('/admin/categories/add', data={
            'category_name': 'Electronics',
            'image': fake_cat_image,
            'description': 'Gadgets and electronic devices'
        }, content_type='multipart/form-data', follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'created successfully', res.data)

        with app.app_context():
            cat = Category.query.filter_by(name='Electronics').first()
            self.assertIsNotNone(cat)
            self.assertEqual(cat.description, 'Gadgets and electronic devices')
            self.assertTrue(cat.image.endswith('.png'))
            cat_id = cat.id

        # 3. View Category List (GET method uses Raw SQL)
        list_res = self.client.get('/admin/categories')
        self.assertEqual(list_res.status_code, 200)
        self.assertIn(b'Electronics', list_res.data)
        self.assertIn(b'Gadgets and electronic devices', list_res.data)

        # 4. View Edit Category Page (GET uses Raw SQL)
        edit_page_res = self.client.get(f'/admin/categories/edit/{cat_id}')
        self.assertEqual(edit_page_res.status_code, 200)
        self.assertIn(b'Electronics', edit_page_res.data)

        # 5. Edit Category with new file upload
        new_fake_image = (io.BytesIO(b'updated image data'), 'smart_electronics.png')
        edit_res = self.client.post(f'/admin/categories/edit/{cat_id}', data={
            'category_name': 'Smart Electronics',
            'image': new_fake_image,
            'description': 'Updated electronics description'
        }, content_type='multipart/form-data', follow_redirects=True)
        self.assertEqual(edit_res.status_code, 200)
        self.assertIn(b'updated successfully', edit_res.data)

        with app.app_context():
            updated_cat = Category.query.get(cat_id)
            self.assertEqual(updated_cat.name, 'Smart Electronics')
            self.assertEqual(updated_cat.description, 'Updated electronics description')

        # 6. Delete Category
        del_res = self.client.post(f'/admin/categories/delete/{cat_id}', follow_redirects=True)
        self.assertEqual(del_res.status_code, 200)
        self.assertIn(b'deleted successfully', del_res.data)

        with app.app_context():
            self.assertIsNone(Category.query.get(cat_id))

    def test_product_file_upload_and_multi_image_crud(self):
        # 1. Login as staff_member
        self.client.post('/login', data={'username': 'staff_member', 'password': 'staff123'}, follow_redirects=True)

        # Create Category in DB first
        with app.app_context():
            cat = Category(name='Audio', description='Headphones and speakers')
            db.session.add(cat)
            db.session.commit()
            cat_id = cat.id
            staff_user = User.query.filter_by(username='staff_member').first()
            staff_id = staff_user.id

        # 2. Add Product with thumbnail file and multiple gallery images
        fake_thumb = (io.BytesIO(b'thumbnail data'), 'main_thumb.jpg')
        fake_img1 = (io.BytesIO(b'gallery img 1'), 'angle_front.png')
        fake_img2 = (io.BytesIO(b'gallery img 2'), 'angle_side.png')
        fake_img3 = (io.BytesIO(b'gallery img 3'), 'angle_box.webp')

        add_res = self.client.post('/admin/products/add', data={
            'title': 'Noise Cancelling Headphones Pro',
            'cost': '75.50',
            'price': '199.99',
            'stock': '25',
            'category_id': str(cat_id),
            'thumbnail': fake_thumb,
            'images': [fake_img1, fake_img2, fake_img3],
            'description': 'Premium noise cancelling wireless headphones'
        }, content_type='multipart/form-data', follow_redirects=True)

        self.assertEqual(add_res.status_code, 200)
        self.assertIn(b'created successfully with 3 gallery image(s)', add_res.data)

        # 3. Verify Product and ProductImage in DB
        with app.app_context():
            prod = Product.query.filter_by(title='Noise Cancelling Headphones Pro').first()
            self.assertIsNotNone(prod)
            self.assertEqual(prod.user_id, staff_id)
            self.assertEqual(float(prod.cost), 75.50)
            self.assertEqual(float(prod.price), 199.99)
            self.assertEqual(prod.stock, 25)
            self.assertEqual(prod.category_id, cat_id)
            self.assertTrue(prod.thumbnail.endswith('.jpg'))

            # Check linked gallery images
            gallery = ProductImage.query.filter_by(product_id=prod.id).all()
            self.assertEqual(len(gallery), 3)
            prod_id = prod.id
            img_to_delete_id = gallery[0].id

        # 4. View Products List
        list_res = self.client.get('/admin/products')
        self.assertEqual(list_res.status_code, 200)
        self.assertIn(b'Noise Cancelling Headphones Pro', list_res.data)
        self.assertIn(b'Audio', list_res.data)
        self.assertIn(b'staff_member', list_res.data)

        # 4b. View Product Details Page
        detail_res = self.client.get(f'/admin/products/{prod_id}')
        self.assertEqual(detail_res.status_code, 200)
        self.assertIn(b'Noise Cancelling Headphones Pro', detail_res.data)
        self.assertIn(b'Pricing & Margins', detail_res.data)
        self.assertIn(b'199.99', detail_res.data)


        # 5. Delete a single gallery image from product
        del_img_res = self.client.post(f'/admin/products/{prod_id}/images/delete/{img_to_delete_id}', follow_redirects=True)
        self.assertEqual(del_img_res.status_code, 200)
        self.assertIn(b'Gallery image removed', del_img_res.data)

        with app.app_context():
            remaining_gallery = ProductImage.query.filter_by(product_id=prod_id).all()
            self.assertEqual(len(remaining_gallery), 2)

        # 6. Edit Product (update details and upload additional image)
        fake_new_img = (io.BytesIO(b'new gallery image'), 'angle_closeup.jpg')
        edit_res = self.client.post(f'/admin/products/edit/{prod_id}', data={
            'title': 'Pro Wireless Studio Headphones',
            'cost': '80.00',
            'price': '229.99',
            'stock': '15',
            'category_id': str(cat_id),
            'images': [fake_new_img],
            'description': 'Updated studio headphones description'
        }, content_type='multipart/form-data', follow_redirects=True)
        self.assertEqual(edit_res.status_code, 200)
        self.assertIn(b'updated successfully', edit_res.data)

        with app.app_context():
            updated_prod = Product.query.get(prod_id)
            self.assertEqual(updated_prod.title, 'Pro Wireless Studio Headphones')
            self.assertEqual(float(updated_prod.price), 229.99)
            self.assertEqual(len(updated_prod.images), 3)

        # 7. Delete Product (cascades and removes gallery records)
        del_prod_res = self.client.post(f'/admin/products/delete/{prod_id}', follow_redirects=True)
        self.assertEqual(del_prod_res.status_code, 200)
        self.assertIn(b'deleted successfully', del_prod_res.data)

        with app.app_context():
            self.assertIsNone(Product.query.get(prod_id))
            self.assertEqual(ProductImage.query.filter_by(product_id=prod_id).count(), 0)


if __name__ == '__main__':
    unittest.main()
