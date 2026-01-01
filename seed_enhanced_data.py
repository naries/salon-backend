"""Seed enhanced data for MVP with superadmin, plans, and service templates

Run this script to create:
- A superadmin user
- Three subscription plans (Free Basic, Standard, Premium)
- Service templates in different categories
- A demo salon with admin user and services

Usage:
    python seed_enhanced_data.py
"""
from app.core.database import SessionLocal
from app.core.security import get_password_hash
from app.models.models import Salon, User, Service, Plan, ServiceTemplate
from datetime import datetime
import json
import re


def generate_slug(name: str, db) -> str:
    """Generate a unique slug from salon name"""
    base_slug = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')
    slug = base_slug
    counter = 1
    while db.query(Salon).filter(Salon.slug == slug).first():
        slug = f"{base_slug}-{counter}"
        counter += 1
    return slug

def seed_enhanced_data():
    db = SessionLocal()
    
    try:
        # Check if data already exists
        existing_superadmin = db.query(User).filter(User.is_superadmin == 1).first()
        if existing_superadmin:
            print("Enhanced data already exists. Skipping seed.")
            return
        
        print("=" * 60)
        print("SEEDING ENHANCED DATA")
        print("=" * 60)
        
        # 1. Create Superadmin
        print("\n📊 Creating Superadmin...")
        The superadmin = User(
            email="superadmin@salonplatform.com",
            hashed_password=get_password_hash("superadmin123"),
            full_name="Platform Administrator",
            is_admin=1,
            is_superadmin=1,
            salon_id=None,  # Superadmin not tied to any salon
            created_at=datetime.utcnow()
        )
        db.add(superadmin)
        db.flush()
        print(f"✓ Created superadmin: {superadmin.email}")
        
        # 2. Create Subscription Plans
        print("\n💳 Creating Subscription Plans...")
        plans_data = [
            {
                "name": "Free Basic",
                "description": "Perfect for getting started with basic salon management",
                "price": 0,  # Free
                "features": json.dumps([
                    "Up to 50 appointments per month",
                    "Basic appointment management",
                    "Customer database",
                    "Email support"
                ]),
                "max_appointments_per_month": 50
            },
            {
                "name": "Standard",
                "description": "Great for growing salons with more features",
                "price": 2999,  # $29.99
                "features": json.dumps([
                    "Up to 200 appointments per month",
                    "Advanced appointment management",
                    "Customer database with history",
                    "SMS notifications",
                    "Priority email support",
                    "Analytics dashboard"
                ]),
                "max_appointments_per_month": 200
            },
            {
                "name": "Premium",
                "description": "Complete solution for established salons",
                "price": 4999,  # $49.99
                "features": json.dumps([
                    "Unlimited appointments",
                    "Full appointment management suite",
                    "Advanced customer CRM",
                    "SMS & Email notifications",
                    "24/7 priority support",
                    "Advanced analytics & reporting",
                    "Multi-location support",A
                    "Custom branding"
                ]),
                "max_appointments_per_month": 0  # 0 = unlimited
            }
        ]
        
        plans = []
        for plan_data in plans_data:
            plan = Plan(**plan_data, created_at=datetime.utcnow())
            db.add(plan)
            db.flush()
            plans.append(plan)
            print(f"✓ Created plan: {plan.name} (${plan.price/100:.2f}/month)")
        
        # 3. Create Service Templates
        print("\n💅 Creating Service Templates...")
        templates_data = [
            # Hair Services
            {"name": "Haircut - Women", "category": "Hair", "default_price": 4500, "default_duration_minutes": 60, "description": "Professional women's haircut and styling"},
            {"name": "Haircut - Men", "category": "Hair", "default_price": 3000, "default_duration_minutes": 45, "description": "Men's haircut and styling"},
            {"name": "Hair Coloring - Full", "category": "Hair", "default_price": 8500, "default_duration_minutes": 120, "description": "Complete hair coloring service"},
            {"name": "Hair Coloring - Touch-up", "category": "Hair", "default_price": 6000, "default_duration_minutes": 90, "description": "Root touch-up and color refresh"},
            {"name": "Highlights", "category": "Hair", "default_price": 9500, "default_duration_minutes": 150, "description": "Full or partial highlights"},
            {"name": "Blow Dry & Style", "category": "Hair", "default_price": 3500, "default_duration_minutes": 45, "description": "Professional blow dry and styling"},
            
            # Nail Services
            {"name": "Manicure - Classic", "category": "Nails", "default_price": 3000, "default_duration_minutes": 45, "description": "Classic manicure with polish"},
            {"name": "Manicure - Gel", "category": "Nails", "default_price": 4500, "default_duration_minutes": 60, "description": "Gel manicure with long-lasting polish"},
            {"name": "Pedicure - Classic", "category": "Nails", "default_price": 4000, "default_duration_minutes": 60, "description": "Classic pedicure with foot treatment"},
            {"name": "Pedicure - Spa", "category": "Nails", "default_price": 5500, "default_duration_minutes": 75, "description": "Luxury spa pedicure"},
            {"name": "Nail Art", "category": "Nails", "default_price": 2000, "default_duration_minutes": 30, "description": "Custom nail art design"},
            
            # Spa & Wellness
            {"name": "Facial - Classic", "category": "Spa", "default_price": 6500, "default_duration_minutes": 75, "description": "Deep cleansing facial treatment"},
            {"name": "Facial - Anti-Aging", "category": "Spa", "default_price": 8500, "default_duration_minutes": 90, "description": "Advanced anti-aging facial"},
            {"name": "Body Massage - 60min", "category": "Spa", "default_price": 7000, "default_duration_minutes": 60, "description": "Full body relaxation massage"},
            {"name": "Body Massage - 90min", "category": "Spa", "default_price": 10000, "default_duration_minutes": 90, "description": "Extended full body massage"},
            
            # Beauty Services
            {"name": "Makeup Application", "category": "Beauty", "default_price": 5000, "default_duration_minutes": 60, "description": "Professional makeup application"},
            {"name": "Bridal Makeup", "category": "Beauty", "default_price": 15000, "default_duration_minutes": 120, "description": "Complete bridal makeup package"},
            {"name": "Eyebrow Shaping", "category": "Beauty", "default_price": 2000, "default_duration_minutes": 30, "description": "Eyebrow shaping and grooming"},
            {"name": "Eyebrow Tinting", "category": "Beauty", "default_price": 2500, "default_duration_minutes": 30, "description": "Professional eyebrow tinting"},
            {"name": "Eyelash Extensions", "category": "Beauty", "default_price": 12000, "default_duration_minutes": 120, "description": "Full set eyelash extensions"},
            {"name": "Eyelash Lift & Tint", "category": "Beauty", "default_price": 6000, "default_duration_minutes": 60, "description": "Lash lift and tinting service"},
            {"name": "Waxing - Full Legs", "category": "Beauty", "default_price": 4500, "default_duration_minutes": 45, "description": "Full leg waxing service"},
            {"name": "Waxing - Half Legs", "category": "Beauty", "default_price": 3000, "default_duration_minutes": 30, "description": "Half leg waxing service"},
            {"name": "Waxing - Bikini", "category": "Beauty", "default_price": 3500, "default_duration_minutes": 30, "description": "Bikini area waxing"},
            {"name": "Waxing - Brazilian", "category": "Beauty", "default_price": 5000, "default_duration_minutes": 45, "description": "Brazilian waxing service"},
            {"name": "Waxing - Arms", "category": "Beauty", "default_price": 3000, "default_duration_minutes": 30, "description": "Full arm waxing"},
            {"name": "Waxing - Underarms", "category": "Beauty", "default_price": 2000, "default_duration_minutes": 20, "description": "Underarm waxing"},
            {"name": "Waxing - Face", "category": "Beauty", "default_price": 2500, "default_duration_minutes": 30, "description": "Facial waxing service"},
            
            # Styling Services
            {"name": "Hair Styling - Updo", "category": "Styling", "default_price": 7000, "default_duration_minutes": 90, "description": "Elegant updo hair styling"},
            {"name": "Hair Styling - Half Up", "category": "Styling", "default_price": 5000, "default_duration_minutes": 60, "description": "Half up hair styling"},
            {"name": "Bridal Hair Styling", "category": "Styling", "default_price": 15000, "default_duration_minutes": 120, "description": "Complete bridal hair styling"},
            {"name": "Hair Styling - Curls", "category": "Styling", "default_price": 4500, "default_duration_minutes": 60, "description": "Professional curls and waves"},
            {"name": "Hair Styling - Braids", "category": "Styling", "default_price": 5500, "default_duration_minutes": 90, "description": "Professional braiding service"},
            {"name": "Hair Extension Application", "category": "Styling", "default_price": 20000, "default_duration_minutes": 180, "description": "Hair extension installation"},
            {"name": "Keratin Treatment", "category": "Styling", "default_price": 18000, "default_duration_minutes": 180, "description": "Smoothing keratin treatment"},
            {"name": "Hair Perming", "category": "Styling", "default_price": 12000, "default_duration_minutes": 150, "description": "Professional perming service"},
            {"name": "Hair Straightening", "category": "Styling", "default_price": 15000, "default_duration_minutes": 180, "description": "Chemical hair straightening"},
        ]
        
        templates = []
        for template_data in templates_data:
            template = ServiceTemplate(**template_data, created_at=datetime.utcnow())
            db.add(template)
            templates.append(template)
        
        db.flush()
        print(f"✓ Created {len(templates)} service templates across multiple categories")
        
        # 4. Create Demo Salon with Free Basic Plan
        print("\n🏪 Creating Demo Salon...")
        demo_salon = Salon(
            name="Bella Salon & Spa",
            address="123 Beauty Street, Style City, SC 12345",
            phone="(555) 123-4567",
            email="contact@bellasalon.com",
            plan_id=plans[0].id,  # Free Basic plan
            is_active=1,
            created_at=datetime.utcnow()
        )
        db.add(demo_salon)
        db.flush()
        print(f"✓ Created demo salon: {demo_salon.name} (Plan: {plans[0].name})")
        
        # 5. Create Demo Salon Admin
        print("\n👤 Creating Demo Salon Admin...")
        demo_admin = User(
            email="admin@bellasalon.com",
            hashed_password=get_password_hash("admin123"),
            full_name="Sarah Johnson",
            is_admin=1,
            is_superadmin=0,
            salon_id=demo_salon.id,
            created_at=datetime.utcnow()
        )
        db.add(demo_admin)
        db.flush()
        print(f"✓ Created salon admin: {demo_admin.email}")
        
        # 6. Add Some Services to Demo Salon (from templates)
        print("\n💇 Adding Services to Demo Salon...")
        demo_service_templates = templates[:8]  # First 8 templates
        for template in demo_service_templates:
            service = Service(
                salon_id=demo_salon.id,
                name=template.name,
                description=template.description,
                price=template.default_price,
                duration_minutes=template.default_duration_minutes,
                created_at=datetime.utcnow()
            )
            db.add(service)
        
        db.commit()
        print(f"✓ Added {len(demo_service_templates)} services to demo salon")
        
        # Summary
        print("\n" + "=" * 60)
        print("✅ ENHANCED DATA SEEDED SUCCESSFULLY!")
        print("=" * 60)
        
        print("\n🔐 SUPERADMIN LOGIN:")
        print(f"   Email: {superadmin.email}")
        print(f"   Password: superadmin123")
        print(f"   Access: All salons and platform management")
        
        print("\n💳 SUBSCRIPTION PLANS:")
        for plan in plans:
            print(f"   • {plan.name}: ${plan.price/100:.2f}/month")
        
        print(f"\n📋 SERVICE TEMPLATES: {len(templates)} templates created")
        print("   Categories: Hair, Nails, Spa, Beauty")
        
        print(f"\n🏪 DEMO SALON:")
        print(f"   Name: {demo_salon.name}")
        print(f"   Slug: {demo_salon.slug}")
        print(f"   URL: http://localhost:3001/{demo_salon.slug}")
        print(f"   Plan: {plans[0].name}")
        print(f"   Admin: {demo_admin.email}")
        print(f"   Password: admin123")
        print(f"   Services: {len(demo_service_templates)} services")
        
        print("\n" + "=" * 60)
        
    except Exception as e:
        db.rollback()
        print(f"\n❌ Error seeding data: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("\n🌱 Starting enhanced data seeding...")
    seed_enhanced_data()
