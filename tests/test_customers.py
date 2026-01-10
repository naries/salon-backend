"""
Unit tests for customer endpoints
"""
import pytest
from fastapi import status
from app.models.models import Customer


@pytest.mark.unit
class TestCustomerAuth:
    """Tests for customer authentication"""
    
    def test_customer_login_success(self, client, test_customer):
        """Test successful customer login"""
        response = client.post(
            "/api/v1/customer-auth/login",
            json={
                "email": "customer@test.com",
                "password": "customerpass123"
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert data["customer"]["email"] == "customer@test.com"
    
    def test_customer_login_invalid_credentials(self, client, test_customer):
        """Test customer login with wrong password"""
        response = client.post(
            "/api/v1/customer-auth/login",
            json={
                "email": "customer@test.com",
                "password": "wrongpassword"
            }
        )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_customer_register_success(self, client, test_salon):
        """Test successful customer registration"""
        response = client.post(
            "/api/v1/customer-auth/register",
            json={
                "full_name": "New Customer",
                "email": "newcustomer@test.com",
                "phone": "+1234567890",
                "password": "newpass123",
                "salon_id": test_salon.id
            }
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["email"] == "newcustomer@test.com"
        assert data["full_name"] == "New Customer"
        assert "hashed_password" not in data
    
    def test_customer_register_duplicate_email(self, client, test_customer, test_salon):
        """Test customer registration with existing email"""
        response = client.post(
            "/api/v1/customer-auth/register",
            json={
                "full_name": "Duplicate Customer",
                "email": test_customer.email,
                "phone": "+9999999999",
                "password": "password123",
                "salon_id": test_salon.id
            }
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "already registered" in response.json()["detail"].lower()
    
    def test_customer_register_invalid_email(self, client, test_salon):
        """Test customer registration with invalid email format"""
        response = client.post(
            "/api/v1/customer-auth/register",
            json={
                "full_name": "Test Customer",
                "email": "not-an-email",
                "phone": "+1234567890",
                "password": "password123",
                "salon_id": test_salon.id
            }
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.unit
class TestCustomerCRUD:
    """Tests for customer CRUD operations"""
    
    def test_get_customers_list(self, client, test_customer, auth_headers):
        """Test retrieving customers list"""
        response = client.get(
            "/api/v1/customers/",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        assert any(c["id"] == test_customer.id for c in data)
    
    def test_get_customer_by_id(self, client, test_customer, auth_headers):
        """Test retrieving a specific customer"""
        response = client.get(
            f"/api/v1/customers/{test_customer.id}",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == test_customer.id
        assert data["email"] == test_customer.email
        assert data["full_name"] == test_customer.full_name
    
    def test_get_nonexistent_customer(self, client, auth_headers):
        """Test retrieving non-existent customer"""
        response = client.get(
            "/api/v1/customers/99999",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_update_customer(self, client, test_customer, auth_headers):
        """Test updating customer information"""
        response = client.put(
            f"/api/v1/customers/{test_customer.id}",
            headers=auth_headers,
            json={
                "full_name": "Updated Customer Name",
                "phone": "+9876543210"
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["full_name"] == "Updated Customer Name"
        assert data["phone"] == "+9876543210"
    
    def test_delete_customer(self, client, test_customer, auth_headers, db):
        """Test deleting a customer"""
        customer_id = test_customer.id
        
        response = client.delete(
            f"/api/v1/customers/{customer_id}",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        
        # Verify customer was deleted
        deleted_customer = db.query(Customer).filter(Customer.id == customer_id).first()
        assert deleted_customer is None
    
    def test_create_customer_by_admin(self, client, test_salon, auth_headers):
        """Test admin creating a customer"""
        response = client.post(
            "/api/v1/customers/",
            headers=auth_headers,
            json={
                "full_name": "Admin Created Customer",
                "email": "admincreated@test.com",
                "phone": "+1111111111",
                "salon_id": test_salon.id
            }
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["full_name"] == "Admin Created Customer"
        assert data["email"] == "admincreated@test.com"


@pytest.mark.unit
class TestCustomerProfile:
    """Tests for customer profile operations"""
    
    def test_get_own_profile(self, client, test_customer, customer_headers):
        """Test customer retrieving their own profile"""
        response = client.get(
            "/api/v1/customers/me",
            headers=customer_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == test_customer.id
        assert data["email"] == test_customer.email
    
    def test_update_own_profile(self, client, test_customer, customer_headers):
        """Test customer updating their own profile"""
        response = client.put(
            "/api/v1/customers/me",
            headers=customer_headers,
            json={
                "full_name": "Self Updated Name",
                "phone": "+5555555555"
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["full_name"] == "Self Updated Name"
        assert data["phone"] == "+5555555555"
    
    def test_get_profile_unauthorized(self, client):
        """Test accessing profile without authentication"""
        response = client.get("/api/v1/customers/me")
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.unit
class TestCustomerSearch:
    """Tests for customer search functionality"""
    
    def test_search_customers_by_name(self, client, test_customer, auth_headers):
        """Test searching customers by name"""
        response = client.get(
            f"/api/v1/customers/?search={test_customer.full_name}",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) > 0
        assert any(c["id"] == test_customer.id for c in data)
    
    def test_search_customers_by_email(self, client, test_customer, auth_headers):
        """Test searching customers by email"""
        response = client.get(
            f"/api/v1/customers/?search={test_customer.email}",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) > 0
        assert any(c["email"] == test_customer.email for c in data)
    
    def test_search_customers_by_phone(self, client, test_customer, auth_headers):
        """Test searching customers by phone"""
        response = client.get(
            f"/api/v1/customers/?search={test_customer.phone}",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) > 0
    
    def test_search_customers_no_results(self, client, auth_headers):
        """Test searching with no matching results"""
        response = client.get(
            "/api/v1/customers/?search=NonExistentCustomer",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 0


@pytest.mark.unit
class TestCustomerAppointments:
    """Tests for customer appointments retrieval"""
    
    def test_get_customer_appointments(self, client, test_customer, test_appointment, customer_headers):
        """Test customer viewing their own appointments"""
        response = client.get(
            "/api/v1/customers/me/appointments",
            headers=customer_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
    
    def test_get_customer_appointments_by_admin(self, client, test_customer, test_appointment, auth_headers):
        """Test admin viewing customer's appointments"""
        response = client.get(
            f"/api/v1/customers/{test_customer.id}/appointments",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)


@pytest.mark.unit
class TestCustomerValidation:
    """Tests for customer data validation"""
    
    def test_create_customer_without_email(self, client, test_salon, auth_headers):
        """Test creating customer without email"""
        response = client.post(
            "/api/v1/customers/",
            headers=auth_headers,
            json={
                "full_name": "No Email Customer",
                "phone": "+1234567890",
                "salon_id": test_salon.id
            }
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_create_customer_without_name(self, client, test_salon, auth_headers):
        """Test creating customer without name"""
        response = client.post(
            "/api/v1/customers/",
            headers=auth_headers,
            json={
                "email": "noname@test.com",
                "phone": "+1234567890",
                "salon_id": test_salon.id
            }
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_update_customer_invalid_email(self, client, test_customer, auth_headers):
        """Test updating customer with invalid email"""
        response = client.put(
            f"/api/v1/customers/{test_customer.id}",
            headers=auth_headers,
            json={
                "email": "not-valid-email"
            }
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
