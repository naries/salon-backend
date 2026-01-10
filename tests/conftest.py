"""
Test configuration and fixtures
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.database import Base, get_db
from app.core.security import get_password_hash
from app.models.models import User, Salon, Plan, Customer, Service, ServiceTemplate
from datetime import datetime


# Create an in-memory SQLite database for testing
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db():
    """Create a fresh database for each test"""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db):
    """Create a test client with overridden database dependency"""
    def override_get_db():
        try:
            yield db
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app=app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def test_plan(db):
    """Create a test plan"""
    plan = Plan(
        name="Basic Plan",
        description="Basic salon plan",
        price=2999,
        monthly_price=2999,
        yearly_price=29990,
        features='["feature1", "feature2"]',
        max_services=10,
        max_appointments_per_month=100,
        is_active=1
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


@pytest.fixture
def test_salon(db, test_plan):
    """Create a test salon"""
    salon = Salon(
        name="Test Salon",
        slug="test-salon",
        address="123 Test St",
        phone="+1234567890",
        email="test@salon.com",
        plan_id=test_plan.id,
        billing_cycle="monthly",
        auto_debit=0,
        opening_hour=9,
        closing_hour=18,
        max_concurrent_slots=3,
        is_active=1
    )
    db.add(salon)
    db.commit()
    db.refresh(salon)
    return salon


@pytest.fixture
def test_admin_user(db, test_salon):
    """Create a test admin user"""
    user = User(
        email="admin@test.com",
        full_name="Test Admin",
        hashed_password=get_password_hash("testpassword123"),
        salon_id=test_salon.id,
        is_admin=1,
        is_superadmin=0
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def test_superadmin_user(db):
    """Create a test superadmin user"""
    user = User(
        email="superadmin@test.com",
        full_name="Test Superadmin",
        hashed_password=get_password_hash("superpassword123"),
        salon_id=None,
        is_admin=1,
        is_superadmin=1
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def test_customer(db, test_salon):
    """Create a test customer"""
    customer = Customer(
        full_name="Test Customer",
        email="customer@test.com",
        phone="+1234567890",
        hashed_password=get_password_hash("customerpass123"),
        salon_id=test_salon.id
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer


@pytest.fixture
def test_service_template(db):
    """Create a test service template"""
    template = ServiceTemplate(
        name="Haircut",
        description="Basic haircut service",
        category="Hair",
        suggested_price=25.00,
        suggested_duration=30
    )
    db.add(template)
    db.commit()
    db.refresh(template)
    return template


@pytest.fixture
def test_service(db, test_salon, test_service_template):
    """Create a test service"""
    service = Service(
        salon_id=test_salon.id,
        name="Haircut",
        description="Professional haircut",
        price=30.00,
        duration=30,
        template_id=test_service_template.id
    )
    db.add(service)
    db.commit()
    db.refresh(service)
    return service


@pytest.fixture
def test_sub_service(db, test_service):
    """Create a test sub-service"""
    from app.models.models import SubService
    sub_service = SubService(
        service_id=test_service.id,
        name="Basic Haircut",
        description="Standard haircut",
        price=25.00,
        duration=30,
        min_hours_notice=2,
        pricing_type="fixed"
    )
    db.add(sub_service)
    db.commit()
    db.refresh(sub_service)
    return sub_service


@pytest.fixture
def test_appointment(db, test_salon, test_customer, test_service, test_sub_service):
    """Create a test appointment"""
    from app.models.models import Appointment
    from datetime import timedelta
    future_date = datetime.utcnow() + timedelta(days=1)
    appointment = Appointment(
        salon_id=test_salon.id,
        customer_id=test_customer.id,
        service_id=test_service.id,
        sub_service_id=test_sub_service.id,
        appointment_date=future_date,
        slot_start=10,
        slot_end=11,
        status="scheduled",
        total_price=25.00
    )
    db.add(appointment)
    db.commit()
    db.refresh(appointment)
    return appointment


@pytest.fixture
def admin_token(client, test_admin_user):
    """Get an admin authentication token"""
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "admin@test.com",
            "password": "testpassword123"
        }
    )
    if response.status_code == 200:
        return response.json()["access_token"]
    return None


@pytest.fixture
def superadmin_token(client, test_superadmin_user):
    """Get a superadmin authentication token"""
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "superadmin@test.com",
            "password": "superpassword123"
        }
    )
    if response.status_code == 200:
        return response.json()["access_token"]
    return None


@pytest.fixture
def customer_token(client, test_customer):
    """Get a customer authentication token"""
    response = client.post(
        "/api/v1/customer-auth/login",
        json={
            "email": "customer@test.com",
            "password": "customerpass123"
        }
    )
    if response.status_code == 200:
        return response.json()["access_token"]
    return None


@pytest.fixture
def auth_headers(admin_token):
    """Get authorization headers for admin"""
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
def superadmin_headers(superadmin_token):
    """Get authorization headers for superadmin"""
    return {"Authorization": f"Bearer {superadmin_token}"}


@pytest.fixture
def customer_headers(customer_token):
    """Get authorization headers for customer"""
    return {"Authorization": f"Bearer {customer_token}"}
