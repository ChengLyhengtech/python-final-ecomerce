from app import app, db, User
from models import Product, Category, ProductImage

def seed():
    with app.app_context():
        # Ensure default admin exists
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin = User(
                username='admin',
                email='admin@store.com',
                phone_number='012345678',
                role='admin',
                profile_image='no-profile.png'
            )
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()

        # Seed categories if needed
        cats = {
            'Audio': ('1790327258_3beca4_electronics_icon.png', 'High-fidelity audio equipment, studio monitors and headphones.'),
            'Computers': ('1790911730_1a00c4_sdfsadfas.jpg', 'Laptops, ultrabooks, mechanical keyboards and accessories.'),
            'Wearables': ('1790737353_96cdb9_dsvdfvfda.jpg', 'Smartwatches, fitness bands and premium wearables.')
        }

        cat_objs = {}
        for name, (img, desc) in cats.items():
            c = Category.query.filter_by(name=name).first()
            if not c:
                c = Category(name=name, image=img, description=desc)
                db.session.add(c)
                db.session.commit()
            cat_objs[name] = c

        # Seed sample products with multiple gallery images if product count < 3
        if Product.query.count() < 3:
            p1 = Product(
                title='Studio Wireless Pro ANC Headphones',
                thumbnail='1790737353_96cdb9_dsvdfvfda.jpg',
                cost=85.00,
                price=199.99,
                stock=18,
                description='Experience studio-grade acoustics and hybrid active noise cancellation with 40-hour playback.',
                user_id=admin.id,
                category_id=cat_objs['Audio'].id
            )
            p2 = Product(
                title='Lenovo ThinkPad X1 Carbon Gen 10',
                thumbnail='1790911730_1a00c4_sdfsadfas.jpg',
                cost=750.00,
                price=1249.99,
                stock=8,
                description='Ultra-lightweight business powerhouse with 14-inch 2.8K OLED display, Intel Core i7, and 16GB RAM.',
                user_id=admin.id,
                category_id=cat_objs['Computers'].id
            )
            p3 = Product(
                title='Galaxy Ultra Smart Sport Watch',
                thumbnail='1790828778_39f144_Gemini_Generated_Image_i7yysii7yysii7yy.jpg',
                cost=140.00,
                price=299.00,
                stock=12,
                description='Titanium chassis smart timepiece featuring advanced biometrics, heart rate monitoring, and GPS tracking.',
                user_id=admin.id,
                category_id=cat_objs['Wearables'].id
            )

            db.session.add_all([p1, p2, p3])
            db.session.commit()

            # Multiple gallery images for p1
            img1_1 = ProductImage(image_url='1790737382_0f9b65_cdsfsf.jpg', product_id=p1.id)
            img1_2 = ProductImage(image_url='1790737382_3da9fa_sdfsadfas.jpg', product_id=p1.id)
            img1_3 = ProductImage(image_url='1790327745_a170b8_Gemini_Generated_Image_i7yysii7yysii7yy.jpg', product_id=p1.id)

            # Multiple gallery images for p2
            img2_1 = ProductImage(image_url='1790911730_7df43d_STU_2617.jpg', product_id=p2.id)
            img2_2 = ProductImage(image_url='1790911730_435c6a_STU_2619.jpg', product_id=p2.id)
            img2_3 = ProductImage(image_url='1790911730_d06b52_STU_2622.jpg', product_id=p2.id)

            # Multiple gallery images for p3
            img3_1 = ProductImage(image_url='1790828778_0a7600_Gemini_Generated_Image_i7yysii7yysii7yy.jpg', product_id=p3.id)
            img3_2 = ProductImage(image_url='1790828778_219d3b_dsvdfvfda.jpg', product_id=p3.id)
            img3_3 = ProductImage(image_url='1790828778_b58b44_cdsfsf.jpg', product_id=p3.id)

            db.session.add_all([img1_1, img1_2, img1_3, img2_1, img2_2, img2_3, img3_1, img3_2, img3_3])
            db.session.commit()
            print("Successfully seeded demo categories and products with multi-image gallery!")

if __name__ == '__main__':
    seed()

