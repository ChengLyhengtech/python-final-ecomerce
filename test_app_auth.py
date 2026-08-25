import unittest
from app import app, db, User


class AuthTestCase(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        self.client = app.test_client()

        with app.app_context():
            db.drop_all()
            db.create_all()

            # Create default admin
            admin = User(
                username='admin',
                email='admin@store.com',
                phone_number='012345678',
                role='admin',
                profile_image='no-profile.png'
            )
            admin.set_password('admin123')
            db.session.add(admin)

            # Create regular user
            user = User(
                username='john',
                email='john@example.com',
                phone_number='098765432',
                role='user',
                profile_image='no-profile.png'
            )
            user.set_password('johnpass123')
            db.session.add(user)

            db.session.commit()

    def test_1_password_hashing(self):
        with app.app_context():
            admin = User.query.filter_by(username='admin').first()
            self.assertTrue(admin.check_password('admin123'))
            self.assertFalse(admin.check_password('wrongpass'))
            self.assertNotEqual(admin.password_hash, 'admin123')

    def test_2_login_required_protection(self):
        # Access admin without login -> should redirect to login with next parameter
        response = self.client.get('/admin/users', follow_redirects=False)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login', response.location)
        self.assertIn('next=/admin/users', response.location)

    def test_3_login_success_and_session(self):
        # Login with email
        response = self.client.post('/login', data={
            'username': 'john@example.com',
            'password': 'johnpass123'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)

        with self.client.session_transaction() as sess:
            self.assertEqual(sess.get('username'), 'john')
            self.assertEqual(sess.get('role'), 'user')
            self.assertEqual(sess.get('email'), 'john@example.com')

    def test_4_login_failure(self):
        response = self.client.post('/login', data={
            'username': 'john@example.com',
            'password': 'wrongpassword'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Invalid username/email or password', response.data)

        with self.client.session_transaction() as sess:
            self.assertIsNone(sess.get('user_id'))

    def test_5_role_based_protection_admin_only(self):
        # Login as regular user
        self.client.post('/login', data={
            'username': 'john',
            'password': 'johnpass123'
        }, follow_redirects=True)

        # Try to access admin dashboard as regular user
        response = self.client.get('/admin/dashboard', follow_redirects=True)
        self.assertIn(b'Access denied', response.data)

    def test_6_admin_access_and_create_user(self):
        # Login as admin
        self.client.post('/login', data={
            'username': 'admin',
            'password': 'admin123'
        }, follow_redirects=True)

        # Access admin users list
        response = self.client.get('/admin/users')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Users Management', response.data)

        # Admin creates new user with email, role, and hashed password
        create_res = self.client.post('/admin/users/add', data={
            'username': 'newstaff',
            'email': 'staff@store.com',
            'password': 'staffpassword',
            'role': 'editor',
            'phone_number': '011223344'
        }, follow_redirects=True)
        self.assertEqual(create_res.status_code, 200)
        self.assertIn(b'created successfully', create_res.data)

        with app.app_context():
            new_u = User.query.filter_by(username='newstaff').first()
            self.assertIsNotNone(new_u)
            self.assertEqual(new_u.email, 'staff@store.com')
            self.assertEqual(new_u.role, 'editor')
            self.assertTrue(new_u.check_password('staffpassword'))

    def test_7_user_registration(self):
        response = self.client.post('/register', data={
            'username': 'alice',
            'email': 'alice@example.com',
            'password': 'password123',
            'confirm_password': 'password123'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Registration successful', response.data)

        with app.app_context():
            alice = User.query.filter_by(username='alice').first()
            self.assertIsNotNone(alice)
            self.assertEqual(alice.role, 'user')
            self.assertTrue(alice.check_password('password123'))

    def test_8_logout(self):
        # Login first
        self.client.post('/login', data={
            'username': 'admin',
            'password': 'admin123'
        })
        with self.client.session_transaction() as sess:
            self.assertIsNotNone(sess.get('user_id'))

        # Logout
        logout_res = self.client.get('/logout', follow_redirects=True)
        self.assertEqual(logout_res.status_code, 200)
        self.assertIn(b'logged out successfully', logout_res.data)

        with self.client.session_transaction() as sess:
            self.assertIsNone(sess.get('user_id'))

    def test_9_staff_access_and_hidden_user_feature(self):
        # Create a staff user
        with app.app_context():
            staff = User(
                username='sammy_staff',
                email='staff@store.com',
                role='staff',
                profile_image='no-profile.png'
            )
            staff.set_password('staff123')
            db.session.add(staff)
            db.session.commit()

        # Login as staff
        login_res = self.client.post('/login', data={
            'username': 'sammy_staff',
            'password': 'staff123'
        }, follow_redirects=True)
        self.assertEqual(login_res.status_code, 200)

        # Staff CAN access dashboard
        dash_res = self.client.get('/admin/dashboard')
        self.assertEqual(dash_res.status_code, 200)
        self.assertIn(b'Dashboard Overview', dash_res.data)
        # Total Users card should be HIDDEN from staff
        self.assertNotIn(b'Total Users', dash_res.data)
        # Users menu item should be HIDDEN in sidebar
        self.assertNotIn(b'admin/users', dash_res.data)

        # Staff CAN access products & categories
        prod_res = self.client.get('/admin/products')
        self.assertEqual(prod_res.status_code, 200)
        cat_res = self.client.get('/admin/categories')
        self.assertEqual(cat_res.status_code, 200)

    def test_10_staff_blocked_from_user_management(self):
        # Create a staff user
        with app.app_context():
            if not User.query.filter_by(username='sammy_staff').first():
                staff = User(
                    username='sammy_staff',
                    email='staff@store.com',
                    role='staff',
                    profile_image='no-profile.png'
                )
                staff.set_password('staff123')
                db.session.add(staff)
                db.session.commit()

        # Login as staff
        self.client.post('/login', data={
            'username': 'sammy_staff',
            'password': 'staff123'
        }, follow_redirects=True)

        # Try to access /admin/users -> should be blocked and redirected
        res = self.client.get('/admin/users', follow_redirects=True)
        self.assertIn(b'Access denied. User Management is restricted to Administrators only.', res.data)
        self.assertIn(b'Dashboard Overview', res.data)


if __name__ == '__main__':
    unittest.main()
