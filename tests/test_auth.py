"""
Unit tests for authentication endpoints
"""
import pytest
from fastapi import status
from app.models.models import User


@pytest.mark.unit
class TestAuthLogin:
    """Tests for login endpoint"""
    
    def test_login_success(self, client, test_admin_user):
        """Test successful login with valid credentials"""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "admin@test.com",
                "password": "testpassword123"
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert "user" in data
        assert data["user"]["email"] == "admin@test.com"
    
    def test_login_invalid_email(self, client, test_admin_user):
        """Test login with non-existent email"""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "nonexistent@test.com",
                "password": "testpassword123"
            }
        )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Incorrect email or password" in response.json()["detail"]
    
    def test_login_invalid_password(self, client, test_admin_user):
        """Test login with incorrect password"""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "admin@test.com",
                "password": "wrongpassword"
            }
        )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Incorrect email or password" in response.json()["detail"]
    
    def test_login_missing_email(self, client):
        """Test login with missing email field"""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "password": "testpassword123"
            }
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_login_missing_password(self, client):
        """Test login with missing password field"""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "admin@test.com"
            }
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_login_creates_activity_log(self, client, test_admin_user, db):
        """Test that login creates an activity log entry"""
        from app.models.models import ActivityLog
        
        initial_log_count = db.query(ActivityLog).count()
        
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "admin@test.com",
                "password": "testpassword123"
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
        final_log_count = db.query(ActivityLog).count()
        assert final_log_count == initial_log_count + 1
        
        # Verify the log entry
        log = db.query(ActivityLog).filter(
            ActivityLog.user_id == test_admin_user.id,
            ActivityLog.action == "login"
        ).first()
        assert log is not None
        assert log.entity_type == "user"


@pytest.mark.unit
class TestAuthRegister:
    """Tests for registration endpoint"""
    
    def test_register_success(self, client, test_salon):
        """Test successful user registration"""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "newuser@test.com",
                "full_name": "New User",
                "password": "newpassword123",
                "salon_id": test_salon.id,
                "is_superadmin": False
            }
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["email"] == "newuser@test.com"
        assert data["full_name"] == "New User"
        assert "hashed_password" not in data  # Password should not be returned
    
    def test_register_duplicate_email(self, client, test_admin_user, test_salon):
        """Test registration with existing email"""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "admin@test.com",
                "full_name": "Another User",
                "password": "password123",
                "salon_id": test_salon.id,
                "is_superadmin": False
            }
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Email already registered" in response.json()["detail"]
    
    def test_register_missing_required_fields(self, client):
        """Test registration with missing required fields"""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "incomplete@test.com"
            }
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_register_invalid_email_format(self, client, test_salon):
        """Test registration with invalid email format"""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "not-an-email",
                "full_name": "Test User",
                "password": "password123",
                "salon_id": test_salon.id
            }
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_register_password_hashing(self, client, test_salon, db):
        """Test that password is properly hashed during registration"""
        plain_password = "myplainpassword123"
        
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "hashtest@test.com",
                "full_name": "Hash Test",
                "password": plain_password,
                "salon_id": test_salon.id
            }
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        
        # Verify password is hashed in database
        user = db.query(User).filter(User.email == "hashtest@test.com").first()
        assert user is not None
        assert user.hashed_password != plain_password
        assert user.hashed_password.startswith("$2b$")  # bcrypt hash prefix
    
    def test_register_creates_activity_log(self, client, test_salon, db):
        """Test that registration creates an activity log entry"""
        from app.models.models import ActivityLog
        
        initial_log_count = db.query(ActivityLog).count()
        
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "newloguser@test.com",
                "full_name": "Log Test User",
                "password": "password123",
                "salon_id": test_salon.id
            }
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        final_log_count = db.query(ActivityLog).count()
        assert final_log_count == initial_log_count + 1


@pytest.mark.unit
class TestSecurityFunctions:
    """Tests for security utility functions"""
    
    def test_password_hashing(self):
        """Test password hashing function"""
        from app.core.security import get_password_hash, verify_password
        
        plain_password = "mysecretpassword"
        hashed = get_password_hash(plain_password)
        
        assert hashed != plain_password
        assert verify_password(plain_password, hashed) is True
        assert verify_password("wrongpassword", hashed) is False
    
    def test_access_token_creation(self):
        """Test JWT access token creation"""
        from app.core.security import create_access_token
        from jose import jwt
        from app.core.config import settings
        from datetime import timedelta
        
        data = {"sub": "test@example.com", "salon_id": 1}
        token = create_access_token(data, expires_delta=timedelta(minutes=30))
        
        assert token is not None
        
        # Decode and verify
        decoded = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        assert decoded["sub"] == "test@example.com"
        assert decoded["salon_id"] == 1
        assert "exp" in decoded
    
    def test_refresh_token_creation(self):
        """Test JWT refresh token creation"""
        from app.core.security import create_refresh_token
        from jose import jwt
        from app.core.config import settings
        
        data = {"sub": "test@example.com", "salon_id": 1}
        token = create_refresh_token(data)
        
        assert token is not None
        
        # Decode and verify
        decoded = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        assert decoded["sub"] == "test@example.com"
        assert decoded["type"] == "refresh"
        assert "exp" in decoded
