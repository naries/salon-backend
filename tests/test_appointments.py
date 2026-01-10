"""
Unit tests for appointment endpoints
"""
import pytest
from fastapi import status
from datetime import datetime, timedelta
from app.models.models import Appointment, SubService


@pytest.fixture
def test_sub_service(db, test_service):
    """Create a test sub-service"""
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


@pytest.mark.unit
class TestAppointmentCreation:
    """Tests for appointment creation"""
    
    def test_create_appointment_success(self, client, test_salon, test_customer, test_sub_service, customer_headers):
        """Test successful appointment creation"""
        future_date = (datetime.utcnow() + timedelta(days=2)).strftime("%Y-%m-%d")
        
        response = client.post(
            "/api/v1/appointments/",
            headers=customer_headers,
            json={
                "salon_id": test_salon.id,
                "sub_service_id": test_sub_service.id,
                "appointment_date": future_date,
                "slot_start": 10,
                "slot_end": 11,
                "notes": "Please be gentle"
            }
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["salon_id"] == test_salon.id
        assert data["sub_service_id"] == test_sub_service.id
        assert data["status"] == "scheduled"
        assert data["total_price"] == test_sub_service.price
    
    def test_create_appointment_unauthorized(self, client, test_salon, test_sub_service):
        """Test appointment creation without authentication"""
        future_date = (datetime.utcnow() + timedelta(days=2)).strftime("%Y-%m-%d")
        
        response = client.post(
            "/api/v1/appointments/",
            json={
                "salon_id": test_salon.id,
                "sub_service_id": test_sub_service.id,
                "appointment_date": future_date,
                "slot_start": 10,
                "slot_end": 11
            }
        )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_create_appointment_past_date(self, client, test_salon, test_sub_service, customer_headers):
        """Test appointment creation with past date"""
        past_date = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")
        
        response = client.post(
            "/api/v1/appointments/",
            headers=customer_headers,
            json={
                "salon_id": test_salon.id,
                "sub_service_id": test_sub_service.id,
                "appointment_date": past_date,
                "slot_start": 10,
                "slot_end": 11
            }
        )
        
        assert response.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_422_UNPROCESSABLE_ENTITY]
    
    def test_create_appointment_invalid_slot(self, client, test_salon, test_sub_service, customer_headers):
        """Test appointment creation with invalid time slot"""
        future_date = (datetime.utcnow() + timedelta(days=2)).strftime("%Y-%m-%d")
        
        response = client.post(
            "/api/v1/appointments/",
            headers=customer_headers,
            json={
                "salon_id": test_salon.id,
                "sub_service_id": test_sub_service.id,
                "appointment_date": future_date,
                "slot_start": 25,  # Invalid hour
                "slot_end": 26
            }
        )
        
        assert response.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_422_UNPROCESSABLE_ENTITY]


@pytest.mark.unit
class TestAppointmentRetrieval:
    """Tests for appointment retrieval"""
    
    def test_get_appointments_admin(self, client, test_appointment, auth_headers):
        """Test retrieving appointments as admin"""
        response = client.get(
            "/api/v1/appointments/",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "appointments" in data
        assert "total" in data
        assert "page" in data
        assert "per_page" in data
        assert isinstance(data["appointments"], list)
    
    def test_get_appointments_with_pagination(self, client, auth_headers):
        """Test appointment pagination"""
        response = client.get(
            "/api/v1/appointments/?page=1&per_page=5",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["page"] == 1
        assert data["per_page"] == 5
    
    def test_get_appointments_with_status_filter(self, client, test_appointment, auth_headers):
        """Test filtering appointments by status"""
        response = client.get(
            "/api/v1/appointments/?status=scheduled",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert all(apt["status"] == "scheduled" for apt in data["appointments"])
    
    def test_get_appointment_by_id(self, client, test_appointment, auth_headers):
        """Test retrieving a specific appointment"""
        response = client.get(
            f"/api/v1/appointments/{test_appointment.id}",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == test_appointment.id
        assert data["status"] == test_appointment.status
    
    def test_get_nonexistent_appointment(self, client, auth_headers):
        """Test retrieving non-existent appointment"""
        response = client.get(
            "/api/v1/appointments/99999",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_get_appointments_unauthorized(self, client):
        """Test retrieving appointments without authentication"""
        response = client.get("/api/v1/appointments/")
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.unit
class TestAppointmentUpdate:
    """Tests for appointment updates"""
    
    def test_update_appointment_status(self, client, test_appointment, auth_headers):
        """Test updating appointment status"""
        response = client.put(
            f"/api/v1/appointments/{test_appointment.id}/status",
            headers=auth_headers,
            json={
                "status": "completed"
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "completed"
    
    def test_cancel_appointment_by_customer(self, client, test_appointment, customer_headers):
        """Test customer canceling their own appointment"""
        response = client.put(
            f"/api/v1/appointments/{test_appointment.id}/cancel",
            headers=customer_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "cancelled"
    
    def test_cancel_appointment_by_admin(self, client, test_appointment, auth_headers):
        """Test admin canceling an appointment"""
        response = client.put(
            f"/api/v1/appointments/{test_appointment.id}/status",
            headers=auth_headers,
            json={
                "status": "cancelled"
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "cancelled"
    
    def test_update_appointment_invalid_status(self, client, test_appointment, auth_headers):
        """Test updating appointment with invalid status"""
        response = client.put(
            f"/api/v1/appointments/{test_appointment.id}/status",
            headers=auth_headers,
            json={
                "status": "invalid_status"
            }
        )
        
        assert response.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_422_UNPROCESSABLE_ENTITY]


@pytest.mark.unit
class TestAppointmentAvailability:
    """Tests for appointment availability checking"""
    
    def test_check_slot_availability(self, client, test_salon, test_sub_service):
        """Test checking time slot availability"""
        future_date = (datetime.utcnow() + timedelta(days=2)).strftime("%Y-%m-%d")
        
        response = client.post(
            "/api/v1/appointments/check-availability",
            json={
                "salon_id": test_salon.id,
                "sub_service_id": test_sub_service.id,
                "appointment_date": future_date,
                "slot_start": 14,
                "slot_end": 15
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "available" in data
        assert isinstance(data["available"], bool)
    
    def test_get_available_slots(self, client, test_salon, test_sub_service):
        """Test retrieving all available slots for a date"""
        future_date = (datetime.utcnow() + timedelta(days=2)).strftime("%Y-%m-%d")
        
        response = client.get(
            f"/api/v1/appointments/available-slots?salon_id={test_salon.id}&date={future_date}"
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)


@pytest.mark.unit
class TestAppointmentAutoCancellation:
    """Tests for automatic appointment cancellation"""
    
    def test_auto_cancel_overdue_appointments(self, db, test_salon, test_customer, test_service, test_sub_service):
        """Test that overdue appointments are auto-cancelled"""
        from app.api.v1.endpoints.appointments import auto_cancel_overdue_appointments
        
        # Create an overdue appointment (25 hours in the past)
        overdue_date = datetime.utcnow() - timedelta(hours=25)
        overdue_appointment = Appointment(
            salon_id=test_salon.id,
            customer_id=test_customer.id,
            service_id=test_service.id,
            sub_service_id=test_sub_service.id,
            appointment_date=overdue_date,
            slot_start=10,
            slot_end=11,
            status="scheduled",
            total_price=25.00
        )
        db.add(overdue_appointment)
        db.commit()
        
        # Run auto-cancellation
        cancelled_count = auto_cancel_overdue_appointments(db, test_salon.id)
        
        assert cancelled_count == 1
        db.refresh(overdue_appointment)
        assert overdue_appointment.status == "cancelled"
    
    def test_auto_cancel_does_not_affect_future_appointments(self, db, test_appointment):
        """Test that future appointments are not auto-cancelled"""
        from app.api.v1.endpoints.appointments import auto_cancel_overdue_appointments
        
        initial_status = test_appointment.status
        
        # Run auto-cancellation
        auto_cancel_overdue_appointments(db, test_appointment.salon_id)
        
        db.refresh(test_appointment)
        assert test_appointment.status == initial_status


@pytest.mark.unit
class TestAppointmentSearch:
    """Tests for appointment search functionality"""
    
    def test_search_appointments_by_customer_name(self, client, test_appointment, auth_headers):
        """Test searching appointments by customer name"""
        response = client.get(
            f"/api/v1/appointments/?search={test_appointment.customer.full_name}",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["appointments"]) > 0
    
    def test_search_appointments_no_results(self, client, auth_headers):
        """Test searching with no matching results"""
        response = client.get(
            "/api/v1/appointments/?search=NonExistentCustomer",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 0
        assert len(data["appointments"]) == 0
