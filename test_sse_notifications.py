"""
SSE Notification Test Script

This script demonstrates how to:
1. Create test notifications
2. Push them to SSE streams
3. Simulate different notification scenarios

Usage:
    python test_sse_notifications.py
"""
import asyncio
import sys
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

from app.core.database import SessionLocal
from app.models.models import User, Salon, Customer, Notification
from app.services.notification_service import NotificationService
from app.core.notification_manager import notification_manager


async def send_test_notification_to_salon(salon_id: int, message: str = "Test notification"):
    """Send a test notification to all admins in a salon"""
    print(f"\n📤 Sending notification to salon {salon_id}...")
    
    notification_data = {
        "id": 999,
        "notification_type": "test",
        "title": "Test Notification",
        "message": message,
        "recipient_type": "salon",
        "recipient_id": None,
        "salon_id": salon_id,
        "entity_type": None,
        "entity_id": None,
        "is_read": False,
        "created_at": "2024-01-15T10:30:00",
        "extra_data": {"test": True}
    }
    
    await notification_manager.send_to_salon_admins(salon_id, notification_data)
    print(f"✅ Notification sent to salon {salon_id}")


async def send_test_notification_to_admin(salon_id: int, user_id: int, message: str = "Test notification"):
    """Send a test notification to a specific admin"""
    print(f"\n📤 Sending notification to admin {user_id} in salon {salon_id}...")
    
    notification_data = {
        "id": 999,
        "notification_type": "test",
        "title": "Direct Admin Notification",
        "message": message,
        "recipient_type": "user",
        "recipient_id": user_id,
        "salon_id": salon_id,
        "entity_type": None,
        "entity_id": None,
        "is_read": False,
        "created_at": "2024-01-15T10:30:00",
        "extra_data": {"test": True, "direct": True}
    }
    
    result = await notification_manager.send_to_specific_admin(salon_id, user_id, notification_data)
    if result:
        print(f"✅ Notification sent to admin {user_id}")
    else:
        print(f"⚠️  Admin {user_id} not connected")


async def send_test_notification_to_customer(customer_id: int, message: str = "Test notification"):
    """Send a test notification to a customer"""
    print(f"\n📤 Sending notification to customer {customer_id}...")
    
    notification_data = {
        "id": 999,
        "notification_type": "test",
        "title": "Customer Notification",
        "message": message,
        "recipient_type": "customer",
        "recipient_id": customer_id,
        "salon_id": 1,
        "entity_type": None,
        "entity_id": None,
        "is_read": False,
        "created_at": "2024-01-15T10:30:00",
        "extra_data": {"test": True}
    }
    
    result = await notification_manager.send_to_customer(customer_id, notification_data)
    if result:
        print(f"✅ Notification sent to customer {customer_id}")
    else:
        print(f"⚠️  Customer {customer_id} not connected")


def show_connection_stats():
    """Display current SSE connection statistics"""
    stats = notification_manager.get_stats()
    
    print("\n📊 SSE Connection Statistics:")
    print(f"  Active admin connections: {stats['active_admin_connections']}")
    print(f"  Active customer connections: {stats['active_customer_connections']}")
    print(f"  Total connections: {stats['total_connections']}")
    
    if stats['admins']:
        print(f"\n  Connected admins (salon_id, user_id):")
        for salon_id, user_id in stats['admins']:
            print(f"    - Salon {salon_id}, User {user_id}")
    
    if stats['customers']:
        print(f"\n  Connected customers:")
        for customer_id in stats['customers']:
            print(f"    - Customer {customer_id}")


def list_salons_and_users():
    """List available salons and their admins for testing"""
    db = SessionLocal()
    try:
        salons = db.query(Salon).all()
        
        if not salons:
            print("\n⚠️  No salons found in database")
            return
        
        print("\n🏢 Available Salons for Testing:")
        for salon in salons:
            print(f"\n  Salon ID: {salon.id}")
            print(f"  Name: {salon.name}")
            print(f"  Slug: {salon.slug}")
            
            # Get admins for this salon
            admins = db.query(User).filter(User.salon_id == salon.id).all()
            if admins:
                print(f"  Admins:")
                for admin in admins:
                    print(f"    - User ID: {admin.id}, Email: {admin.email}, Role: {admin.role}")
            else:
                print(f"  No admins found")
        
        # List customers
        customers = db.query(Customer).limit(5).all()
        if customers:
            print(f"\n👥 Sample Customers:")
            for customer in customers:
                print(f"  - Customer ID: {customer.id}, Phone: {customer.phone_number}")
    
    finally:
        db.close()


async def interactive_menu():
    """Interactive menu for testing SSE notifications"""
    while True:
        print("\n" + "="*60)
        print("SSE Notification Test Menu")
        print("="*60)
        print("1. Show connection statistics")
        print("2. List salons and users")
        print("3. Send notification to salon (all admins)")
        print("4. Send notification to specific admin")
        print("5. Send notification to customer")
        print("6. Send multiple test notifications (stress test)")
        print("0. Exit")
        print("="*60)
        
        choice = input("\nEnter your choice: ").strip()
        
        if choice == "0":
            print("\n👋 Goodbye!")
            break
        
        elif choice == "1":
            show_connection_stats()
        
        elif choice == "2":
            list_salons_and_users()
        
        elif choice == "3":
            salon_id = input("Enter salon ID: ").strip()
            message = input("Enter message (or press Enter for default): ").strip()
            if not message:
                message = "Test notification from script"
            try:
                await send_test_notification_to_salon(int(salon_id), message)
            except ValueError:
                print("❌ Invalid salon ID")
        
        elif choice == "4":
            salon_id = input("Enter salon ID: ").strip()
            user_id = input("Enter user ID: ").strip()
            message = input("Enter message (or press Enter for default): ").strip()
            if not message:
                message = "Direct notification from script"
            try:
                await send_test_notification_to_admin(int(salon_id), int(user_id), message)
            except ValueError:
                print("❌ Invalid IDs")
        
        elif choice == "5":
            customer_id = input("Enter customer ID: ").strip()
            message = input("Enter message (or press Enter for default): ").strip()
            if not message:
                message = "Customer notification from script"
            try:
                await send_test_notification_to_customer(int(customer_id), message)
            except ValueError:
                print("❌ Invalid customer ID")
        
        elif choice == "6":
            salon_id = input("Enter salon ID for stress test: ").strip()
            count = input("How many notifications? (default 10): ").strip()
            try:
                salon_id = int(salon_id)
                count = int(count) if count else 10
                
                print(f"\n🔄 Sending {count} notifications to salon {salon_id}...")
                for i in range(count):
                    await send_test_notification_to_salon(
                        salon_id,
                        f"Stress test notification #{i+1}"
                    )
                    await asyncio.sleep(0.5)  # Small delay between notifications
                
                print(f"\n✅ Sent {count} notifications")
            except ValueError:
                print("❌ Invalid input")
        
        else:
            print("❌ Invalid choice")


def main():
    """Main entry point"""
    print("\n" + "="*60)
    print("SSE Notification Test Script")
    print("="*60)
    print("\n📝 Instructions:")
    print("1. Start the FastAPI server in another terminal:")
    print("   uvicorn app.main:app --reload")
    print("\n2. Connect to SSE endpoint in a browser or tool:")
    print("   Browser: Open /api/v1/notifications/stream with valid auth")
    print("   cURL: curl -N -H 'Authorization: Bearer TOKEN' http://localhost:8000/api/v1/notifications/stream")
    print("\n3. Use this script to send test notifications")
    print("\n⚠️  Make sure you have active SSE connections before sending notifications!")
    print("="*60)
    
    input("\nPress Enter to continue...")
    
    # Run interactive menu
    asyncio.run(interactive_menu())


if __name__ == "__main__":
    main()
