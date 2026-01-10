# Salon Backend - Test Suite

This directory contains comprehensive unit tests for the salon-backend application.

## Test Structure

```
tests/
├── conftest.py              # Test configuration and shared fixtures
├── test_auth.py            # Authentication and authorization tests
├── test_salons.py          # Salon management tests
├── test_appointments.py    # Appointment booking and management tests
├── test_customers.py       # Customer management tests
├── test_services.py        # Service and sub-service tests
└── test_models.py          # Database model tests
```

## Running Tests

### Install Test Dependencies

```bash
pip install -r requirements.txt
```

The test dependencies include:
- `pytest` - Testing framework
- `pytest-asyncio` - Async test support
- `pytest-cov` - Code coverage reporting
- `httpx` - HTTP client for testing
- `faker` - Generate fake data for tests

### Run All Tests

```bash
pytest
```

### Run Specific Test File

```bash
pytest tests/test_auth.py
```

### Run Specific Test Class

```bash
pytest tests/test_auth.py::TestAuthLogin
```

### Run Specific Test

```bash
pytest tests/test_auth.py::TestAuthLogin::test_login_success
```

### Run Tests with Coverage

```bash
pytest --cov=app --cov-report=html
```

This will generate an HTML coverage report in `htmlcov/index.html`.

### Run Tests by Marker

```bash
# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# Run only slow tests
pytest -m slow
```

### Run Tests in Verbose Mode

```bash
pytest -v
```

### Run Tests and Stop on First Failure

```bash
pytest -x
```

## Test Fixtures

The `conftest.py` file provides shared fixtures that can be used across all tests:

### Database Fixtures
- `db` - Fresh database session for each test
- `client` - FastAPI test client

### Model Fixtures
- `test_plan` - Sample subscription plan
- `test_salon` - Sample salon
- `test_admin_user` - Sample admin user
- `test_superadmin_user` - Sample superadmin user
- `test_customer` - Sample customer
- `test_service_template` - Sample service template
- `test_service` - Sample service
- `test_sub_service` - Sample sub-service

### Authentication Fixtures
- `admin_token` - JWT token for admin
- `superadmin_token` - JWT token for superadmin
- `customer_token` - JWT token for customer
- `auth_headers` - Authorization headers for admin
- `superadmin_headers` - Authorization headers for superadmin
- `customer_headers` - Authorization headers for customer

## Test Coverage

The test suite covers:

### Authentication (`test_auth.py`)
- User login (valid/invalid credentials)
- User registration
- Token generation
- Password hashing
- Activity logging

### Salons (`test_salons.py`)
- Salon registration
- Salon information updates
- Salon hours management
- Slug generation and uniqueness
- Service creation from templates

### Appointments (`test_appointments.py`)
- Appointment creation
- Appointment retrieval and filtering
- Appointment status updates
- Appointment cancellation
- Availability checking
- Auto-cancellation of overdue appointments
- Search functionality

### Customers (`test_customers.py`)
- Customer authentication
- Customer registration
- CRUD operations
- Profile management
- Search functionality
- Appointment history

### Services (`test_services.py`)
- Service CRUD operations
- Service templates
- Sub-services
- Data validation
- Search and filtering by category

### Models (`test_models.py`)
- Model creation and validation
- Unique constraints
- Relationships between models

## Writing New Tests

### Basic Test Structure

```python
import pytest
from fastapi import status

@pytest.mark.unit
class TestYourFeature:
    """Tests for your feature"""
    
    def test_something(self, client, auth_headers):
        """Test description"""
        response = client.get(
            "/api/v1/endpoint/",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["field"] == "expected_value"
```

### Using Fixtures

```python
def test_with_fixtures(self, client, test_salon, test_customer, auth_headers):
    """Test using multiple fixtures"""
    response = client.post(
        "/api/v1/appointments/",
        headers=auth_headers,
        json={
            "salon_id": test_salon.id,
            "customer_id": test_customer.id
        }
    )
    assert response.status_code == status.HTTP_201_CREATED
```

### Testing Database Changes

```python
def test_database_change(self, client, auth_headers, db):
    """Test that verifies database changes"""
    from app.models.models import YourModel
    
    initial_count = db.query(YourModel).count()
    
    # Perform action
    response = client.post("/api/v1/endpoint/", headers=auth_headers, json={...})
    
    final_count = db.query(YourModel).count()
    assert final_count == initial_count + 1
```

## Best Practices

1. **Use descriptive test names** - Test names should clearly describe what is being tested
2. **One assertion per concept** - Keep tests focused on one specific behavior
3. **Use fixtures** - Reuse common setup code via fixtures
4. **Test edge cases** - Include tests for invalid inputs, empty data, etc.
5. **Mock external dependencies** - Use mocks for external APIs, file systems, etc.
6. **Clean test data** - Each test should be independent and not rely on other tests
7. **Use markers** - Tag tests appropriately (unit, integration, slow)

## Continuous Integration

These tests are designed to run in CI/CD pipelines. The test database uses SQLite in-memory, so no external database is required.

## Troubleshooting

### Import Errors

If you get import errors, ensure you're running tests from the project root:

```bash
cd /Users/ajiboyeayobami/Documents/salon-backend
pytest
```

### Database Errors

If you encounter database-related errors, check that:
- The test database is using SQLite (configured in conftest.py)
- Models are properly imported
- Fixtures are properly set up

### Token/Authentication Errors

If authentication tests fail:
- Check that the SECRET_KEY is properly set
- Verify password hashing is working correctly
- Ensure token expiration is set appropriately

## Contributing

When adding new features:
1. Write tests first (TDD approach recommended)
2. Ensure all tests pass before committing
3. Maintain test coverage above 80%
4. Document any new fixtures or test utilities
