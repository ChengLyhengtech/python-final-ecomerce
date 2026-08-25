from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

from .user import User
from .category import Category
from .product import Product

__all__ = ['db', 'User', 'Category', 'Product']
