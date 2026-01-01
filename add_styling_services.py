"""Add more beauty and styling service templates

Usage:
    python add_styling_services.py
"""
from app.core.database import SessionLocal
from app.models.models import ServiceTemplate
from datetime import datetime


def add_styling_services():
    db = SessionLocal()
    
    try:
        print("=" * 60)
        print("ADDING STYLING & BEAUTY SERVICES")
        print("=" * 60)
        
        # New services to add
        new_services = [
            # Additional Beauty Services
            {"name": "Eyebrow Tinting", "category": "Beauty", "default_price": 2500, "default_duration_minutes": 30, "description": "Professional eyebrow tinting"},
            {"name": "Eyelash Lift & Tint", "category": "Beauty", "default_price": 6000, "default_duration_minutes": 60, "description": "Lash lift and tinting service"},
            {"name": "Waxing - Half Legs", "category": "Beauty", "default_price": 3000, "default_duration_minutes": 30, "description": "Half leg waxing service"},
            {"name": "Waxing - Bikini", "category": "Beauty", "default_price": 3500, "default_duration_minutes": 30, "description": "Bikini area waxing"},
            {"name": "Waxing - Brazilian", "category": "Beauty", "default_price": 5000, "default_duration_minutes": 45, "description": "Brazilian waxing service"},
            {"name": "Waxing - Arms", "category": "Beauty", "default_price": 3000, "default_duration_minutes": 30, "description": "Full arm waxing"},
            {"name": "Waxing - Underarms", "category": "Beauty", "default_price": 2000, "default_duration_minutes": 20, "description": "Underarm waxing"},
            {"name": "Waxing - Face", "category": "Beauty", "default_price": 2500, "default_duration_minutes": 30, "description": "Facial waxing service"},
            
            # Styling Services (New Category)
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
        
        added_count = 0
        for service_data in new_services:
            # Check if service already exists
            existing = db.query(ServiceTemplate).filter(
                ServiceTemplate.name == service_data["name"]
            ).first()
            
            if not existing:
                template = ServiceTemplate(**service_data, created_at=datetime.utcnow())
                db.add(template)
                added_count += 1
                print(f"✓ Added: {service_data['name']} ({service_data['category']})")
            else:
                print(f"- Skipped (exists): {service_data['name']}")
        
        db.commit()
        print(f"\n✓ Successfully added {added_count} new service templates")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ Error: {str(e)}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    add_styling_services()
