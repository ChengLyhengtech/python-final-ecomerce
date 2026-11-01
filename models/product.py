from . import db

class Product(db.Model):
    __tablename__ = 'products'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    thumbnail = db.Column(db.String(255), nullable=True)
    cost = db.Column(db.Numeric(10, 2), nullable=False, default=0.0)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    stock = db.Column(db.Integer, nullable=False, default=0)
    description = db.Column(db.Text, nullable=True)
    # Foreign Keys linking to User and Category tables
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)
    images = db.relationship('ProductImage', backref='product', lazy=True, cascade='all, delete-orphan')

