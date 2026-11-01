from . import db


class ProductImage(db.Model):
    __tablename__ = 'product_images'

    id = db.Column(db.Integer, primary_key=True)
    image_url = db.Column(db.String(255), nullable=False)

    # Foreign Key linking to Product table
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)