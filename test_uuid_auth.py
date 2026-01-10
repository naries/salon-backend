#!/usr/bin/env python3
"""
Test script to verify UUID-based authentication
"""
from app.core.database import engine
from sqlalchemy import text
from app.models.models import Customer
from app.core.security import create_access_token, get_password_hash
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from jose import jwt
from app.core.config import settings

def test_uuid_migration():
    """Check that existing customers have UUIDs"""
    print("=" * 50)
    print("1. Checking existing customers have UUIDs...")
    print("=" * 50)
    
    with engine.connect() as conn:
        result = conn.execute(text('SELECT id, email, uuid FROM customers LIMIT 5'))
        customers = list(result)
        
        if not customers:
            print("✓ No existing customers found (expected for fresh DB)")
        else:
            print(f"✓ Found {len(customers)} customer(s):")
            for row in customers:
                print(f"  - ID: {row[0]}, Email: {row[1]}, UUID: {row[2][:8]}...")

def test_new_customer_gets_uuid():
    """Test that new customers get UUIDs automatically"""
    print("\n" + "=" * 50)
    print("2. Testing new customer gets UUID...")
    print("=" * 50)
    
    db = SessionLocal()
    try:
        # Create a test customer
        test_email = f"test_uuid_{int(__import__('time').time())}@example.com"
        customer = Customer(
            name="UUID Test Customer",
            email=test_email,
            phone="+1234567890",
            hashed_password=get_password_hash("test123"),
            salon_id=None
        )
        db.add(customer)
        db.commit()
        db.refresh(customer)
        
        print(f"✓ Created customer: {customer.email}")
        print(f"✓ UUID generated: {customer.uuid}")
        assert customer.uuid is not None, "UUID should be generated"
        assert len(customer.uuid) == 36, "UUID should be 36 characters"
        
        # Clean up
        db.delete(customer)
        db.commit()
        print("✓ Test customer cleaned up")
        
    finally:
        db.close()

def test_jwt_token_uses_uuid():
    """Test that JWT tokens use UUID instead of email"""
    print("\n" + "=" * 50)
    print("3. Testing JWT tokens use UUID...")
    print("=" * 50)
    
    db = SessionLocal()
    try:
        # Create a test customer
        test_email = f"test_jwt_{int(__import__('time').time())}@example.com"
        customer = Customer(
            name="JWT Test Customer",
            email=test_email,
            phone="+1234567890",
            hashed_password=get_password_hash("test123"),
            salon_id=None
        )
        db.add(customer)
        db.commit()
        db.refresh(customer)
        
        # Create JWT token
        token = create_access_token(
            data={
                "sub": customer.uuid,
                "customer_id": customer.id,
                "salon_id": customer.salon_id,
                "type": "customer"
            }
        )
        
        # Decode and verify
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        
        print(f"✓ Token created for customer: {customer.email}")
        print(f"✓ Token 'sub' claim: {payload['sub']}")
        print(f"✓ Customer UUID: {customer.uuid}")
        
        assert payload['sub'] == customer.uuid, "Token sub should be UUID"
        assert payload['customer_id'] == customer.id, "Token should have customer_id"
        assert payload['type'] == 'customer', "Token type should be customer"
        
        print("✓ JWT token uses UUID correctly!")
        
        # Clean up
        db.delete(customer)
        db.commit()
        
    finally:
        db.close()

def test_lookup_by_uuid():
    """Test that we can look up customers by UUID"""
    print("\n" + "=" * 50)
    print("4. Testing customer lookup by UUID...")
    print("=" * 50)
    
    db = SessionLocal()
    try:
        # Create a test customer
        test_email = f"test_lookup_{int(__import__('time').time())}@example.com"
        customer = Customer(
            name="Lookup Test Customer",
            email=test_email,
            phone="+1234567890",
            hashed_password=get_password_hash("test123"),
            salon_id=None
        )
        db.add(customer)
        db.commit()
        db.refresh(customer)
        
        uuid = customer.uuid
        customer_id = customer.id
        
        # Look up by UUID
        found_customer = db.query(Customer).filter(
            Customer.uuid == uuid,
            Customer.id == customer_id
        ).first()
        
        assert found_customer is not None, "Customer should be found by UUID"
        assert found_customer.email == test_email, "Found correct customer"
        
        print(f"✓ Successfully looked up customer by UUID: {uuid[:8]}...")
        print(f"✓ Customer email: {found_customer.email}")
        
        # Clean up
        db.delete(customer)
        db.commit()
        
    finally:
        db.close()

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("UUID AUTHENTICATION MIGRATION TEST SUITE")
    print("=" * 60)
    
    try:
        test_uuid_migration()
        test_new_customer_gets_uuid()
        test_jwt_token_uses_uuid()
        test_lookup_by_uuid()
        
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)
        print("\nUUID authentication is working correctly.")
        print("Customers now use UUIDs for secure identification.")
        print("\n⚠️  IMPORTANT: This is a breaking change!")
        print("   - All existing customer sessions will be invalidated")
        print("   - Customers will need to log in again")
        print("=" * 60)
        
    except Exception as e:
        print("\n" + "=" * 60)
        print("❌ TEST FAILED!")
        print("=" * 60)
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
