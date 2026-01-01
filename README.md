Backend development notes
-------------------------

Quick start (SQLite - recommended for local dev)

1. Ensure `.env` contains:

   DATABASE_URL=sqlite:///./dev.db

2. Start the app (from the `backend` folder):

```bash
source ../.venv/bin/activate
uvicorn app.main:app --reload
```

This will create `dev.db` in the `backend` folder and run `Base.metadata.create_all`.

Optional: Run Postgres locally with Docker (if you want parity with production)

```bash
docker run --name salon-db -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=postgres -p 5432:5432 -d postgres:15
# then set DATABASE_URL in .env to:
# DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/postgres
```

Notes
- `backend/app/core/database.py` was updated to support `sqlite` connect args.
# Salon Management Backend

FastAPI backend for the Salon Management System with PostgreSQL database.

## Setup

### Prerequisites
- Docker and Docker Compose
- Python 3.11+ (for local development)

### Running with Docker

1. Build and start the containers:
```bash
docker-compose up --build
```

2. The API will be available at:
   - API: http://localhost:8000
   - API Docs: http://localhost:8000/docs
   - PostgreSQL: localhost:5432

### Local Development

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Copy `.env.example` to `.env` and update values

4. Start PostgreSQL (using Docker):
```bash
docker-compose up db
```

5. Run the application:
```bash
uvicorn app.main:app --reload
```

## API Endpoints

- `GET /` - Welcome message
- `GET /health` - Health check
- `GET /api/v1/appointments` - Get all appointments
- `GET /api/v1/customers` - Get all customers
- `GET /api/v1/services` - Get all services

See `/docs` for complete API documentation.
