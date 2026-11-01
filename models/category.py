from . import db

class Category(db.Model):
    __tablename__ = 'categories'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False, unique=True)
    image = db.Column(db.String(255), nullable=True)
    description = db.Column(db.Text, nullable=True)

    # Relationship: One category can have multiple products
    products = db.relationship('Product', backref='category', lazy=True)
