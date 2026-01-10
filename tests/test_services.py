"""
Unit tests for service endpoints
"""
import pytest
from fastapi import status
from app.models.models import Service, SubService, ServiceTemplate


@pytest.mark.unit
class TestServiceCRUD:
    """Tests for service CRUD operations"""
    
    def test_create_service(self, client, test_salon, test_service_template, auth_headers):
        """Test creating a new service"""
        response = client.post(
            "/api/v1/services/",
            headers=auth_headers,
            json={
                "name": "New Service",
                "description": "A brand new service",
                "price": 50.00,
                "duration": 60,
                "template_id": test_service_template.id
            }
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["name"] == "New Service"
        assert data["price"] == 50.00
        assert data["duration"] == 60
        assert data["salon_id"] == test_salon.id
    
    def test_get_services_list(self, client, test_service, auth_headers):
        """Test retrieving services list"""
        response = client.get(
            "/api/v1/services/",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        assert any(s["id"] == test_service.id for s in data)
    
    def test_get_service_by_id(self, client, test_service, auth_headers):
        """Test retrieving a specific service"""
        response = client.get(
            f"/api/v1/services/{test_service.id}",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == test_service.id
        assert data["name"] == test_service.name
        assert data["price"] == test_service.price
    
    def test_get_nonexistent_service(self, client, auth_headers):
        """Test retrieving non-existent service"""
        response = client.get(
            "/api/v1/services/99999",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_update_service(self, client, test_service, auth_headers):
        """Test updating service information"""
        response = client.put(
            f"/api/v1/services/{test_service.id}",
            headers=auth_headers,
            json={
                "name": "Updated Service Name",
                "price": 35.00,
                "duration": 45
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "Updated Service Name"
        assert data["price"] == 35.00
        assert data["duration"] == 45
    
    def test_delete_service(self, client, test_service, auth_headers, db):
        """Test deleting a service"""
        service_id = test_service.id
        
        response = client.delete(
            f"/api/v1/services/{service_id}",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        
        # Verify service was deleted
        deleted_service = db.query(Service).filter(Service.id == service_id).first()
        assert deleted_service is None
    
    def test_create_service_unauthorized(self, client, test_service_template):
        """Test creating service without authentication"""
        response = client.post(
            "/api/v1/services/",
            json={
                "name": "Unauthorized Service",
                "price": 25.00,
                "duration": 30,
                "template_id": test_service_template.id
            }
        )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.unit
class TestServiceTemplates:
    """Tests for service templates"""
    
    def test_get_service_templates(self, client, test_service_template):
        """Test retrieving service templates"""
        response = client.get("/api/v1/service-templates/")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        assert any(t["id"] == test_service_template.id for t in data)
    
    def test_get_service_template_by_id(self, client, test_service_template):
        """Test retrieving a specific service template"""
        response = client.get(f"/api/v1/service-templates/{test_service_template.id}")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == test_service_template.id
        assert data["name"] == test_service_template.name
    
    def test_create_service_template_superadmin(self, client, superadmin_headers):
        """Test creating service template as superadmin"""
        response = client.post(
            "/api/v1/service-templates/",
            headers=superadmin_headers,
            json={
                "name": "New Template",
                "description": "A new service template",
                "category": "Hair",
                "suggested_price": 30.00,
                "suggested_duration": 45
            }
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["name"] == "New Template"
        assert data["category"] == "Hair"
    
    def test_create_service_template_non_superadmin(self, client, auth_headers):
        """Test that non-superadmin cannot create service template"""
        response = client.post(
            "/api/v1/service-templates/",
            headers=auth_headers,
            json={
                "name": "Unauthorized Template",
                "category": "Nails",
                "suggested_price": 20.00,
                "suggested_duration": 30
            }
        )
        
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.unit
class TestSubServices:
    """Tests for sub-service operations"""
    
    def test_create_sub_service(self, client, test_service, auth_headers):
        """Test creating a sub-service"""
        response = client.post(
            "/api/v1/sub-services/",
            headers=auth_headers,
            json={
                "service_id": test_service.id,
                "name": "Premium Cut",
                "description": "Premium haircut service",
                "price": 45.00,
                "duration": 45,
                "min_hours_notice": 2,
                "pricing_type": "fixed"
            }
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["name"] == "Premium Cut"
        assert data["price"] == 45.00
        assert data["service_id"] == test_service.id
    
    def test_get_sub_services_by_service(self, client, test_service, test_sub_service, auth_headers):
        """Test retrieving sub-services for a service"""
        response = client.get(
            f"/api/v1/sub-services/?service_id={test_service.id}",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
    
    def test_get_sub_service_by_id(self, client, test_sub_service, auth_headers):
        """Test retrieving a specific sub-service"""
        response = client.get(
            f"/api/v1/sub-services/{test_sub_service.id}",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == test_sub_service.id
        assert data["name"] == test_sub_service.name
    
    def test_update_sub_service(self, client, test_sub_service, auth_headers):
        """Test updating sub-service"""
        response = client.put(
            f"/api/v1/sub-services/{test_sub_service.id}",
            headers=auth_headers,
            json={
                "name": "Updated Sub Service",
                "price": 30.00
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "Updated Sub Service"
        assert data["price"] == 30.00
    
    def test_delete_sub_service(self, client, test_sub_service, auth_headers, db):
        """Test deleting a sub-service"""
        sub_service_id = test_sub_service.id
        
        response = client.delete(
            f"/api/v1/sub-services/{sub_service_id}",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        
        # Verify sub-service was deleted
        deleted = db.query(SubService).filter(SubService.id == sub_service_id).first()
        assert deleted is None
    
    def test_create_sub_service_invalid_service(self, client, auth_headers):
        """Test creating sub-service with non-existent service"""
        response = client.post(
            "/api/v1/sub-services/",
            headers=auth_headers,
            json={
                "service_id": 99999,
                "name": "Invalid Sub Service",
                "price": 25.00,
                "duration": 30,
                "pricing_type": "fixed"
            }
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.unit
class TestServiceValidation:
    """Tests for service data validation"""
    
    def test_create_service_negative_price(self, client, test_service_template, auth_headers):
        """Test creating service with negative price"""
        response = client.post(
            "/api/v1/services/",
            headers=auth_headers,
            json={
                "name": "Invalid Service",
                "price": -10.00,
                "duration": 30,
                "template_id": test_service_template.id
            }
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_create_service_zero_duration(self, client, test_service_template, auth_headers):
        """Test creating service with zero duration"""
        response = client.post(
            "/api/v1/services/",
            headers=auth_headers,
            json={
                "name": "Invalid Service",
                "price": 25.00,
                "duration": 0,
                "template_id": test_service_template.id
            }
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_create_service_missing_required_fields(self, client, auth_headers):
        """Test creating service with missing required fields"""
        response = client.post(
            "/api/v1/services/",
            headers=auth_headers,
            json={
                "name": "Incomplete Service"
            }
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.unit
class TestServiceSearch:
    """Tests for service search functionality"""
    
    def test_search_services_by_name(self, client, test_service, auth_headers):
        """Test searching services by name"""
        response = client.get(
            f"/api/v1/services/?search={test_service.name}",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) > 0
        assert any(s["id"] == test_service.id for s in data)
    
    def test_search_services_no_results(self, client, auth_headers):
        """Test searching services with no matches"""
        response = client.get(
            "/api/v1/services/?search=NonExistentService",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 0


@pytest.mark.unit
class TestServiceByCategory:
    """Tests for filtering services by category"""
    
    def test_get_services_by_category(self, client, test_service, auth_headers):
        """Test retrieving services by category"""
        response = client.get(
            "/api/v1/services/?category=Hair",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
    
    def test_get_services_invalid_category(self, client, auth_headers):
        """Test retrieving services with invalid category"""
        response = client.get(
            "/api/v1/services/?category=NonExistent",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 0
