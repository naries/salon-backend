"""
Unit tests for salon endpoints
"""
import pytest
from fastapi import status
from app.models.models import Salon, User, Service


@pytest.mark.unit
class TestSalonRegistration:
    """Tests for salon registration endpoint"""
    
    def test_register_salon_success(self, client, test_plan, test_service_template, db):
        """Test successful salon registration"""
        response = client.post(
            "/api/v1/salons/register",
            json={
                "name": "New Salon",
                "address": "456 New St",
                "phone": "+1987654321",
                "email": "newsalon@test.com",
                "admin_full_name": "Salon Admin",
                "admin_email": "salonadmin@test.com",
                "admin_password": "adminpass123",
                "selected_service_template_ids": [test_service_template.id],
                "plan_id": test_plan.id,
                "billing_cycle": "monthly",
                "auto_debit": 0
            }
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["name"] == "New Salon"
        assert data["email"] == "newsalon@test.com"
        assert data["slug"] == "new-salon"
        assert data["plan_id"] == test_plan.id
        
        # Verify admin user was created
        admin = db.query(User).filter(User.email == "salonadmin@test.com").first()
        assert admin is not None
        assert admin.is_admin == 1
        assert admin.salon_id == data["id"]
    
    def test_register_salon_duplicate_email(self, client, test_salon, test_plan, test_service_template):
        """Test registration with existing salon email"""
        response = client.post(
            "/api/v1/salons/register",
            json={
                "name": "Duplicate Salon",
                "email": test_salon.email,
                "address": "789 Dup St",
                "phone": "+1111111111",
                "admin_full_name": "Admin Name",
                "admin_email": "newadmin@test.com",
                "admin_password": "password123",
                "selected_service_template_ids": [test_service_template.id],
                "plan_id": test_plan.id,
                "billing_cycle": "monthly"
            }
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Salon with this email already exists" in response.json()["detail"]
    
    def test_register_salon_duplicate_admin_email(self, client, test_admin_user, test_plan, test_service_template):
        """Test registration with existing admin email"""
        response = client.post(
            "/api/v1/salons/register",
            json={
                "name": "Another Salon",
                "email": "anothersalon@test.com",
                "address": "789 Another St",
                "phone": "+1222222222",
                "admin_full_name": "Admin Name",
                "admin_email": test_admin_user.email,
                "admin_password": "password123",
                "selected_service_template_ids": [test_service_template.id],
                "plan_id": test_plan.id,
                "billing_cycle": "monthly"
            }
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "User with this email already exists" in response.json()["detail"]
    
    def test_register_salon_invalid_plan(self, client, test_service_template):
        """Test registration with non-existent plan"""
        response = client.post(
            "/api/v1/salons/register",
            json={
                "name": "Test Salon",
                "email": "test@test.com",
                "address": "123 Test St",
                "phone": "+1234567890",
                "admin_full_name": "Admin",
                "admin_email": "admin@test.com",
                "admin_password": "password123",
                "selected_service_template_ids": [test_service_template.id],
                "plan_id": 9999,
                "billing_cycle": "monthly"
            }
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Selected plan not found" in response.json()["detail"]
    
    def test_register_salon_slug_generation(self, client, test_plan, test_service_template, db):
        """Test that unique slug is generated from salon name"""
        # Register first salon
        response1 = client.post(
            "/api/v1/salons/register",
            json={
                "name": "Unique Salon",
                "email": "unique1@test.com",
                "address": "123 St",
                "phone": "+1111111111",
                "admin_full_name": "Admin 1",
                "admin_email": "admin1@test.com",
                "admin_password": "pass123",
                "selected_service_template_ids": [test_service_template.id],
                "plan_id": test_plan.id,
                "billing_cycle": "monthly"
            }
        )
        assert response1.status_code == status.HTTP_201_CREATED
        assert response1.json()["slug"] == "unique-salon"
        
        # Register salon with same name
        response2 = client.post(
            "/api/v1/salons/register",
            json={
                "name": "Unique Salon",
                "email": "unique2@test.com",
                "address": "456 St",
                "phone": "+2222222222",
                "admin_full_name": "Admin 2",
                "admin_email": "admin2@test.com",
                "admin_password": "pass123",
                "selected_service_template_ids": [test_service_template.id],
                "plan_id": test_plan.id,
                "billing_cycle": "monthly"
            }
        )
        assert response2.status_code == status.HTTP_201_CREATED
        assert response2.json()["slug"] == "unique-salon-1"
    
    def test_register_salon_creates_services_from_templates(self, client, test_plan, test_service_template, db):
        """Test that services are created from selected templates"""
        response = client.post(
            "/api/v1/salons/register",
            json={
                "name": "Service Test Salon",
                "email": "servicetest@test.com",
                "address": "789 Service St",
                "phone": "+3333333333",
                "admin_full_name": "Service Admin",
                "admin_email": "serviceadmin@test.com",
                "admin_password": "pass123",
                "selected_service_template_ids": [test_service_template.id],
                "plan_id": test_plan.id,
                "billing_cycle": "monthly"
            }
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        salon_id = response.json()["id"]
        
        # Verify services were created
        services = db.query(Service).filter(Service.salon_id == salon_id).all()
        assert len(services) > 0
        assert any(s.template_id == test_service_template.id for s in services)


@pytest.mark.unit
class TestSalonUpdate:
    """Tests for salon update endpoints"""
    
    def test_update_salon_hours_success(self, client, test_salon, auth_headers):
        """Test successful salon hours update"""
        response = client.put(
            f"/api/v1/salons/{test_salon.id}/hours",
            headers=auth_headers,
            json={
                "opening_hour": 8,
                "closing_hour": 20,
                "max_concurrent_slots": 5
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["opening_hour"] == 8
        assert data["closing_hour"] == 20
        assert data["max_concurrent_slots"] == 5
    
    def test_update_salon_info_success(self, client, test_salon, auth_headers):
        """Test successful salon information update"""
        response = client.put(
            f"/api/v1/salons/{test_salon.id}",
            headers=auth_headers,
            json={
                "name": "Updated Salon Name",
                "address": "999 Updated St",
                "phone": "+9999999999"
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "Updated Salon Name"
        assert data["address"] == "999 Updated St"
        assert data["phone"] == "+9999999999"
    
    def test_update_salon_unauthorized(self, client, test_salon):
        """Test salon update without authentication"""
        response = client.put(
            f"/api/v1/salons/{test_salon.id}",
            json={
                "name": "Unauthorized Update"
            }
        )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.unit
class TestSalonGet:
    """Tests for salon retrieval endpoints"""
    
    def test_get_salon_by_id(self, client, test_salon):
        """Test retrieving salon by ID"""
        response = client.get(f"/api/v1/salons/{test_salon.id}")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == test_salon.id
        assert data["name"] == test_salon.name
        assert data["slug"] == test_salon.slug
    
    def test_get_salon_by_slug(self, client, test_salon):
        """Test retrieving salon by slug"""
        response = client.get(f"/api/v1/salons/slug/{test_salon.slug}")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["slug"] == test_salon.slug
        assert data["name"] == test_salon.name
    
    def test_get_nonexistent_salon(self, client):
        """Test retrieving non-existent salon"""
        response = client.get("/api/v1/salons/99999")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_list_salons(self, client, test_salon, superadmin_headers):
        """Test listing all salons (superadmin only)"""
        response = client.get(
            "/api/v1/salons",
            headers=superadmin_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        assert any(s["id"] == test_salon.id for s in data)


@pytest.mark.unit
class TestSlugGeneration:
    """Tests for slug generation utility function"""
    
    def test_slug_from_normal_name(self, db):
        """Test slug generation from normal salon name"""
        from app.api.v1.endpoints.salons import generate_slug
        
        slug = generate_slug("Beautiful Salon", db)
        assert slug == "beautiful-salon"
    
    def test_slug_from_name_with_special_chars(self, db):
        """Test slug generation with special characters"""
        from app.api.v1.endpoints.salons import generate_slug
        
        slug = generate_slug("Salon & Spa #1", db)
        assert slug == "salon-spa-1"
    
    def test_slug_from_name_with_spaces(self, db):
        """Test slug generation with multiple spaces"""
        from app.api.v1.endpoints.salons import generate_slug
        
        slug = generate_slug("My   Great   Salon", db)
        assert slug == "my-great-salon"
    
    def test_slug_uniqueness(self, db, test_salon):
        """Test that slug generation ensures uniqueness"""
        from app.api.v1.endpoints.salons import generate_slug
        
        # test_salon already has slug "test-salon"
        slug = generate_slug("Test Salon", db)
        assert slug == "test-salon-1"
