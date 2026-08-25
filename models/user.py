from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from . import db


class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    phone_number = db.Column(db.String(30), nullable=True)
    create_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    role = db.Column(db.String(80), nullable=False, default='user')
    profile_image = db.Column(db.String(255), nullable=True, default='no-profile.png')

    # Relationship: One user can create/own multiple products
    products = db.relationship('Product', backref='owner', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)

    def is_admin(self):
        return (self.role or '').lower() == 'admin'

    def is_staff(self):
        return (self.role or '').lower() in ['staff', 'editor']

    def can_access_admin(self):
        return (self.role or '').lower() in ['admin', 'staff', 'editor']

    def __repr__(self):
        return f'<User {self.username} ({self.role})>'
