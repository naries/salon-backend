"""
Unit tests for models
"""
import pytest
from datetime import datetime
from app.models.models import User, Salon, Customer, Service, Appointment
from app.core.security import get_password_hash


@pytest.mark.unit
class TestUserModel:
    """Tests for User model"""
    
    def test_create_user(self, db, test_salon):
        """Test creating a user"""
        user = User(
            email="test@example.com",
            full_name="Test User",
            hashed_password=get_password_hash("password"),
            salon_id=test_salon.id,
            is_admin=1,
            is_superadmin=0
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        
        assert user.id is not None
        assert user.email == "test@example.com"
        assert user.full_name == "Test User"
        assert user.is_admin == 1
    
    def test_user_email_unique(self, db, test_admin_user):
        """Test that user email must be unique"""
        duplicate_user = User(
            email=test_admin_user.email,
            full_name="Duplicate",
            hashed_password=get_password_hash("password"),
            salon_id=test_admin_user.salon_id,
            is_admin=1
        )
        db.add(duplicate_user)
        
        with pytest.raises(Exception):
            db.commit()


@pytest.mark.unit
class TestSalonModel:
    """Tests for Salon model"""
    
    def test_create_salon(self, db, test_plan):
        """Test creating a salon"""
        salon = Salon(
            name="Test Salon",
            slug="test-salon-model",
            email="salon@test.com",
            plan_id=test_plan.id,
            is_active=1
        )
        db.add(salon)
        db.commit()
        db.refresh(salon)
        
        assert salon.id is not None
        assert salon.name == "Test Salon"
        assert salon.slug == "test-salon-model"
        assert salon.is_active == 1
    
    def test_salon_slug_unique(self, db, test_salon):
        """Test that salon slug must be unique"""
        duplicate_salon = Salon(
            name="Another Salon",
            slug=test_salon.slug,
            email="another@test.com",
            plan_id=test_salon.plan_id,
            is_active=1
        )
        db.add(duplicate_salon)
        
        with pytest.raises(Exception):
            db.commit()


@pytest.mark.unit
class TestCustomerModel:
    """Tests for Customer model"""
    
    def test_create_customer(self, db, test_salon):
        """Test creating a customer"""
        customer = Customer(
            full_name="Test Customer",
            email="customer@test.com",
            phone="+1234567890",
            hashed_password=get_password_hash("password"),
            salon_id=test_salon.id
        )
        db.add(customer)
        db.commit()
        db.refresh(customer)
        
        assert customer.id is not None
        assert customer.full_name == "Test Customer"
        assert customer.email == "customer@test.com"
    
    def test_customer_without_password(self, db, test_salon):
        """Test creating customer without password (walk-in)"""
        customer = Customer(
            full_name="Walk-in Customer",
            email="walkin@test.com",
            phone="+9999999999",
            salon_id=test_salon.id
        )
        db.add(customer)
        db.commit()
        db.refresh(customer)
        
        assert customer.id is not None
        assert customer.hashed_password is None


@pytest.mark.unit
class TestServiceModel:
    """Tests for Service model"""
    
    def test_create_service(self, db, test_salon, test_service_template):
        """Test creating a service"""
        service = Service(
            salon_id=test_salon.id,
            name="Test Service",
            description="A test service",
            price=25.00,
            duration=30,
            template_id=test_service_template.id
        )
        db.add(service)
        db.commit()
        db.refresh(service)
        
        assert service.id is not None
        assert service.name == "Test Service"
        assert service.price == 25.00
        assert service.duration == 30


@pytest.mark.unit
class TestAppointmentModel:
    """Tests for Appointment model"""
    
    def test_create_appointment(self, db, test_salon, test_customer, test_service, test_sub_service):
        """Test creating an appointment"""
        appointment_date = datetime.utcnow()
        appointment = Appointment(
            salon_id=test_salon.id,
            customer_id=test_customer.id,
            service_id=test_service.id,
            sub_service_id=test_sub_service.id,
            appointment_date=appointment_date,
            slot_start=10,
            slot_end=11,
            status="scheduled",
            total_price=25.00
        )
        db.add(appointment)
        db.commit()
        db.refresh(appointment)
        
        assert appointment.id is not None
        assert appointment.salon_id == test_salon.id
        assert appointment.customer_id == test_customer.id
        assert appointment.status == "scheduled"
    
    def test_appointment_relationships(self, db, test_appointment):
        """Test appointment model relationships"""
        assert test_appointment.customer is not None
        assert test_appointment.service is not None
        assert test_appointment.salon is not None
        assert test_appointment.sub_service is not None
