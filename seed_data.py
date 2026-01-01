"""Seed initial data for development

Run this script to create:
- A demo salon
- An admin user for the salon
- Some sample services

Usage:
    python seed_data.py
"""
from app.core.database import SessionLocal
from app.core.security import get_password_hash
from app.models.models import Salon, User, Service
from datetime import datetime

def seed_data():
    db = SessionLocal()
    
    try:
        # Check if data already exists
        existing_salon = db.query(Salon).first()
        if existing_salon:
            print("Data already exists. Skipping seed.")
            return
        
        # Create a demo salon
        salon = Salon(
            name="Bella Salon & Spa",
            address="123 Beauty Street, Style City, SC 12345",
            phone="(555) 123-4567",
            email="contact@bellasalon.com",
            created_at=datetime.utcnow()
        )
        db.add(salon)
        db.flush()
        
        print(f"✓ Created salon: {salon.name} (ID: {salon.id})")
        
        # Create an admin user
        admin_user = User(
            email="admin@bellasalon.com",
            hashed_password=get_password_hash("admin123"),
            full_name="Sarah Johnson",
            is_admin=1,
            salon_id=salon.id,
            created_at=datetime.utcnow()
        )
        db.add(admin_user)
        db.flush()
        
        print(f"✓ Created admin user: {admin_user.email}")
        print(f"  Password: admin123")
        
        # Create sample services
        services = [
            Service(
                salon_id=salon.id,
                name="Haircut & Styling",
                description="Professional haircut with styling",
                price=4500,  # $45.00 in cents
                duration_minutes=60
            ),
            Service(
                salon_id=salon.id,
                name="Hair Coloring",
                description="Full hair coloring service",
                price=8500,  # $85.00
                duration_minutes=120
            ),
            Service(
                salon_id=salon.id,
                name="Manicure",
                description="Complete nail care and polish",
                price=3000,  # $30.00
                duration_minutes=45
            ),
            Service(
                salon_id=salon.id,
                name="Pedicure",
                description="Relaxing foot treatment",
                price=4000,  # $40.00
                duration_minutes=60
            ),
            Service(
                salon_id=salon.id,
                name="Facial Treatment",
                description="Deep cleansing facial",
                price=6500,  # $65.00
                duration_minutes=75
            ),
        ]
        
        for service in services:
            db.add(service)
        
        db.commit()
        print(f"✓ Created {len(services)} services")
        
        print("\n" + "="*50)
        print("✅ Seed data created successfully!")
        print("="*50)
        print(f"\nSalon: {salon.name}")
        print(f"Admin Login:")
        print(f"  Email: {admin_user.email}")
        print(f"  Password: admin123")
        print(f"\nServices created: {len(services)}")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error seeding data: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("Seeding database with initial data...")
    seed_data()
