"""
Seed script to populate product categories and products for all salons
"""
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from app.models.models import Salon, ProductCategory, Product
from datetime import datetime
import os

# Database URL (synchronous version)
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://salon_user:salon_password@localhost:5432/salon_db")

# Sample categories with descriptions
CATEGORIES = [
    {"name": "Hair Care", "description": "Shampoos, conditioners, hair treatments and styling products"},
    {"name": "Skin Care", "description": "Facial cleansers, moisturizers, serums and masks"},
    {"name": "Nail Care", "description": "Nail polish, treatments, tools and accessories"},
    {"name": "Hair Coloring", "description": "Hair dyes, bleaches, toners and color treatments"},
    {"name": "Styling Tools", "description": "Hair dryers, straighteners, curling irons and brushes"},
    {"name": "Body Care", "description": "Body lotions, scrubs, oils and bath products"},
    {"name": "Makeup", "description": "Cosmetics, foundations, lipsticks and beauty tools"},
]

# Sample products for each category
PRODUCTS_BY_CATEGORY = {
    "Hair Care": [
        {"name": "Moisturizing Shampoo", "description": "Deep hydration for dry hair", "price": 25.99, "discount": 10},
        {"name": "Protein Conditioner", "description": "Strengthening conditioner with keratin", "price": 28.99, "discount": 15},
        {"name": "Hair Repair Mask", "description": "Intensive treatment for damaged hair", "price": 35.50, "discount": 0},
        {"name": "Volumizing Spray", "description": "Adds body and fullness to fine hair", "price": 18.99, "discount": 5},
    ],
    "Skin Care": [
        {"name": "Gentle Facial Cleanser", "description": "pH-balanced daily face wash", "price": 22.00, "discount": 0},
        {"name": "Vitamin C Serum", "description": "Brightening and anti-aging serum", "price": 45.00, "discount": 20},
        {"name": "Hyaluronic Moisturizer", "description": "Deep hydration for all skin types", "price": 38.50, "discount": 10},
        {"name": "Clay Face Mask", "description": "Detoxifying mask for oily skin", "price": 29.99, "discount": 0},
    ],
    "Nail Care": [
        {"name": "Gel Nail Polish Set", "description": "Long-lasting gel polish in 12 colors", "price": 45.00, "discount": 15},
        {"name": "Nail Strengthener", "description": "Treatment for weak and brittle nails", "price": 15.99, "discount": 0},
        {"name": "Professional Nail Kit", "description": "Complete manicure tool set", "price": 32.50, "discount": 10},
        {"name": "Cuticle Oil", "description": "Nourishing oil for healthy cuticles", "price": 12.99, "discount": 5},
    ],
    "Hair Coloring": [
        {"name": "Permanent Hair Color", "description": "Long-lasting color in multiple shades", "price": 29.99, "discount": 0},
        {"name": "Bleach Powder", "description": "Professional lightening powder", "price": 24.50, "discount": 10},
        {"name": "Color Toner", "description": "Neutralizes unwanted tones", "price": 18.99, "discount": 0},
        {"name": "Root Touch-Up Kit", "description": "Quick cover for gray roots", "price": 14.99, "discount": 20},
    ],
    "Styling Tools": [
        {"name": "Professional Hair Dryer", "description": "Ionic technology with multiple settings", "price": 89.99, "discount": 15},
        {"name": "Ceramic Flat Iron", "description": "Straightener with temperature control", "price": 75.00, "discount": 10},
        {"name": "Curling Wand Set", "description": "Interchangeable barrels for various curls", "price": 65.50, "discount": 20},
        {"name": "Round Brush Set", "description": "Professional styling brush collection", "price": 28.99, "discount": 0},
    ],
    "Body Care": [
        {"name": "Body Butter", "description": "Rich moisturizer for dry skin", "price": 24.99, "discount": 10},
        {"name": "Sugar Body Scrub", "description": "Exfoliating scrub with natural oils", "price": 19.99, "discount": 0},
        {"name": "Massage Oil", "description": "Relaxing aromatherapy blend", "price": 22.50, "discount": 15},
        {"name": "Bath Salts", "description": "Mineral-rich soaking salts", "price": 16.99, "discount": 5},
    ],
    "Makeup": [
        {"name": "Foundation Set", "description": "Multiple shades for all skin tones", "price": 42.00, "discount": 10},
        {"name": "Eyeshadow Palette", "description": "20 colors for day and night looks", "price": 38.50, "discount": 15},
        {"name": "Lipstick Collection", "description": "Long-wearing formula in trending colors", "price": 25.99, "discount": 0},
        {"name": "Makeup Brush Set", "description": "Professional quality synthetic brushes", "price": 55.00, "discount": 20},
    ],
}


def seed_data():
    """Populate categories and products for all salons"""
    engine = create_engine(DATABASE_URL, echo=False)
    SessionLocal = sessionmaker(bind=engine)
    
    with SessionLocal() as session:
        try:
            # Get all salons
            result = session.execute(text("SELECT id, name FROM salons"))
            salons = result.fetchall()
            
            if not salons:
                print("No salons found. Please create salons first.")
                return
            
            print(f"\nFound {len(salons)} salon(s)")
            
            for salon_id, salon_name in salons:
                print(f"\n{'='*60}")
                print(f"Populating data for: {salon_name} (ID: {salon_id})")
                print(f"{'='*60}")
                
                # Create categories for this salon
                category_map = {}
                for cat_data in CATEGORIES:
                    category = ProductCategory(
                        salon_id=salon_id,
                        name=cat_data["name"],
                        description=cat_data["description"],
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow()
                    )
                    session.add(category)
                    session.flush()  # Get the ID
                    category_map[cat_data["name"]] = category.id
                    print(f"  ✓ Created category: {cat_data['name']}")
                
                # Create products for each category
                product_count = 0
                for category_name, products in PRODUCTS_BY_CATEGORY.items():
                    category_id = category_map[category_name]
                    
                    for prod_data in products:
                        product = Product(
                            salon_id=salon_id,
                            category_id=category_id,
                            name=prod_data["name"],
                            description=prod_data["description"],
                            price=int(prod_data["price"] * 100),  # Convert to cents
                            discount_percentage=prod_data["discount"],
                            quantity=50,  # Starting inventory
                            is_active=1,
                            created_at=datetime.utcnow(),
                            updated_at=datetime.utcnow()
                        )
                        session.add(product)
                        product_count += 1
                
                print(f"  ✓ Created {product_count} products across {len(CATEGORIES)} categories")
            
            # Commit all changes
            session.commit()
            
            print(f"\n{'='*60}")
            print("✅ Seeding completed successfully!")
            print(f"{'='*60}")
            print(f"\nSummary:")
            print(f"  • Salons processed: {len(salons)}")
            print(f"  • Categories per salon: {len(CATEGORIES)}")
            print(f"  • Products per salon: {sum(len(p) for p in PRODUCTS_BY_CATEGORY.values())}")
            print(f"  • Total categories created: {len(salons) * len(CATEGORIES)}")
            print(f"  • Total products created: {len(salons) * sum(len(p) for p in PRODUCTS_BY_CATEGORY.values())}")
            
        except Exception as e:
            session.rollback()
            print(f"\n❌ Error during seeding: {str(e)}")
            raise


if __name__ == "__main__":
    print("Starting seed process for categories and products...")
    seed_data()
