# Salon Management Backend - Setup Guide

## Quick Start

### 1. Start the Backend

```bash
cd backend
docker-compose up --build
```

This will start:
- PostgreSQL database on `localhost:5432`
- FastAPI backend on `http://localhost:8000`

### 2. Seed the Database

In a new terminal, run the seed script to create initial data:

```bash
cd backend
docker-compose exec backend python seed_data.py
```

This creates:
- A demo salon: "Bella Salon & Spa"
- An admin user with credentials:
  - **Email:** `admin@bellasalon.com`
  - **Password:** `admin123`
- 5 sample services (Haircut, Coloring, Manicure, Pedicure, Facial)

### 3. Access the API

- **API Base:** http://localhost:8000
- **Interactive Docs:** http://localhost:8000/docs
- **Alternative Docs:** http://localhost:8000/redoc

## Authentication

All admin endpoints require authentication. Use the `/api/v1/auth/login` endpoint to get a JWT token.

### Login Example

```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@bellasalon.com", "password": "admin123"}'
```

Response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer"
}
```

### Using the Token

Include the token in the Authorization header:

```bash
curl -X GET "http://localhost:8000/api/v1/appointments" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

## API Endpoints

### Authentication
- `POST /api/v1/auth/login` - Login and get JWT token
- `POST /api/v1/auth/register` - Register new admin user

### Appointments (Requires Authentication)
- `GET /api/v1/appointments` - Get all appointments for your salon
- `POST /api/v1/appointments` - Create new appointment
- `GET /api/v1/appointments/{id}` - Get specific appointment
- `PUT /api/v1/appointments/{id}` - Update appointment status
- `DELETE /api/v1/appointments/{id}` - Delete appointment

### Services (Requires Authentication)
- `GET /api/v1/services` - Get all services for your salon
- `POST /api/v1/services` - Create new service
- `GET /api/v1/services/{id}` - Get specific service
- `PUT /api/v1/services/{id}` - Update service
- `DELETE /api/v1/services/{id}` - Delete service

### Customers (Requires Authentication)
- `GET /api/v1/customers` - Get all customers
- `POST /api/v1/customers` - Create new customer
- `GET /api/v1/customers/{id}` - Get specific customer
- `PUT /api/v1/customers/{id}` - Update customer
- `DELETE /api/v1/customers/{id}` - Delete customer

## Database Models

### Salon
- Multi-tenant support - each salon is isolated
- Has many users (admins), appointments, and services

### User
- Admin users belong to a specific salon
- Can only access data for their salon
- Authentication via JWT tokens

### Appointment
- Links customer, service, and salon
- Filtered by salon_id for security
- Statuses: scheduled, completed, cancelled

### Service
- Salon-specific services
- Price stored in cents
- Duration in minutes

### Customer
- Shared across salons (by email)
- Stores contact information

## Security Features

- **JWT Authentication**: Secure token-based auth
- **Password Hashing**: Bcrypt encryption
- **Salon Isolation**: Admins can only access their salon's data
- **CORS Protection**: Configured for frontend origins
- **SQL Injection Protection**: SQLAlchemy ORM

## Development

### Database Migrations

The app uses Alembic for database migrations:

```bash
# Create a new migration
docker-compose exec backend alembic revision --autogenerate -m "description"

# Run migrations
docker-compose exec backend alembic upgrade head

# Rollback
docker-compose exec backend alembic downgrade -1
```

### Environment Variables

Copy `.env.example` to `.env` and update:

```env
DATABASE_URL=postgresql://salon_user:salon_password@db:5432/salon_db
SECRET_KEY=your-secret-key-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

### Logs

View backend logs:
```bash
docker-compose logs -f backend
```

View database logs:
```bash
docker-compose logs -f db
```

## Troubleshooting

### Can't connect to database
```bash
# Check if containers are running
docker-compose ps

# Restart services
docker-compose restart
```

### Reset database
```bash
docker-compose down -v
docker-compose up --build
docker-compose exec backend python seed_data.py
```

### Port already in use
If port 8000 or 5432 is in use, update the port mappings in `docker-compose.yml`.

## Testing with cURL

### 1. Login
```bash
export TOKEN=$(curl -s -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@bellasalon.com", "password": "admin123"}' \
  | jq -r '.access_token')
```

### 2. Get Services
```bash
curl -X GET "http://localhost:8000/api/v1/services" \
  -H "Authorization: Bearer $TOKEN"
```

### 3. Create Appointment
```bash
curl -X POST "http://localhost:8000/api/v1/appointments" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "customer_name": "John Doe",
    "customer_email": "john@example.com",
    "customer_phone": "(555) 123-4567",
    "service_id": 1,
    "appointment_date": "2025-11-20T14:00:00",
    "notes": "First time customer"
  }'
```

### 4. Get Appointments
```bash
curl -X GET "http://localhost:8000/api/v1/appointments" \
  -H "Authorization: Bearer $TOKEN"
```
