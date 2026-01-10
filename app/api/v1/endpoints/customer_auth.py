from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime
from app.core.database import get_db
from app.core.security import (
    get_password_hash,
    authenticate_customer,
    create_access_token,
    get_current_customer
)
from app.models.models import Customer, SalonCustomer
from app.schemas.schemas import (
    CustomerRegister,
    CustomerLogin,
    CustomerToken,
    CustomerTokenWithInfo,
    CustomerAuthResponse,
    PlatformCustomerRegister
)

router = APIRouter()


def get_or_create_salon_customer(
    db: Session,
    salon_id: int,
    customer_id: int,
    source: str = "appointment"
) -> SalonCustomer:
    """
    Get existing salon-customer relationship or create a new one.
    This is called when a customer books an appointment or makes a purchase.
    """
    # Check if relationship already exists
    existing = db.query(SalonCustomer).filter(
        SalonCustomer.salon_id == salon_id,
        SalonCustomer.customer_id == customer_id
    ).first()
    
    if existing:
        # Update last interaction
        existing.last_interaction_at = datetime.utcnow()
        db.commit()
        return existing
    
    # Create new relationship
    salon_customer = SalonCustomer(
        salon_id=salon_id,
        customer_id=customer_id,
        source=source,
        first_interaction_at=datetime.utcnow(),
        last_interaction_at=datetime.utcnow()
    )
    db.add(salon_customer)
    db.commit()
    db.refresh(salon_customer)
    return salon_customer


@router.post("/register", response_model=CustomerAuthResponse, status_code=status.HTTP_201_CREATED)
def register_customer(
    customer_data: CustomerRegister,
    db: Session = Depends(get_db)
):
    """
    Register a new customer account.
    
    This endpoint now supports both:
    - Platform-wide registration (no salon_id) - customer can book/purchase from any salon
    - Legacy salon-specific registration (with salon_id) - creates salon relationship automatically
    """
    # Check if email already exists
    existing_customer = db.query(Customer).filter(Customer.email == customer_data.email).first()
    if existing_customer:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new platform customer
    hashed_password = get_password_hash(customer_data.password)
    db_customer = Customer(
        name=customer_data.name,
        email=customer_data.email,
        phone=customer_data.phone,
        hashed_password=hashed_password,
        salon_id=customer_data.salon_id,  # Legacy field - kept for backward compatibility
        platform_joined_at=datetime.utcnow()
    )
    db.add(db_customer)
    db.commit()
    db.refresh(db_customer)
    
    # If salon_id was provided, create the salon-customer relationship
    if customer_data.salon_id:
        get_or_create_salon_customer(
            db=db,
            salon_id=customer_data.salon_id,
            customer_id=db_customer.id,
            source="manual"  # They registered directly for this salon
        )
    
    return db_customer


@router.post("/platform-register", response_model=CustomerTokenWithInfo, status_code=status.HTTP_201_CREATED)
def register_platform_customer(
    customer_data: PlatformCustomerRegister,
    db: Session = Depends(get_db)
):
    """
    Register a new platform-wide customer account.
    
    Customer signs up once and can then book/purchase from any salon.
    Salon relationships are created automatically when they interact with a salon.
    Returns access token and customer info for immediate login.
    """
    # Check if email already exists
    existing_customer = db.query(Customer).filter(Customer.email == customer_data.email).first()
    if existing_customer:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new platform customer (no salon_id)
    hashed_password = get_password_hash(customer_data.password)
    db_customer = Customer(
        name=customer_data.name,
        email=customer_data.email,
        phone=customer_data.phone,
        hashed_password=hashed_password,
        salon_id=None,  # Platform-wide customer
        platform_joined_at=datetime.utcnow()
    )
    db.add(db_customer)
    db.commit()
    db.refresh(db_customer)
    
    # Create access token for immediate login with UUID
    access_token = create_access_token(
        data={
            "sub": db_customer.uuid,  # Use UUID instead of email
            "customer_id": db_customer.id,
            "salon_id": None,
            "type": "customer"
        }
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "customer": db_customer
    }


@router.post("/login", response_model=CustomerTokenWithInfo)
def login_customer(
    customer_credentials: CustomerLogin,
    db: Session = Depends(get_db)
):
    """
    Login customer and return access token with customer info.
    
    Works for both platform-wide and legacy salon-specific customers.
    Token includes customer_id (salon_id is optional and may be None).
    """
    customer = authenticate_customer(db, customer_credentials.email, customer_credentials.password)
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access token with UUID as subject - salon_id may be None for platform customers
    access_token = create_access_token(
        data={
            "sub": customer.uuid,  # Use UUID instead of email for better security
            "customer_id": customer.id,
            "salon_id": customer.salon_id,  # May be None for platform customers
            "type": "customer"  # Identify this as a customer token
        }
    )
    
    return {
        "access_token": access_token, 
        "token_type": "bearer",
        "customer": customer
    }


@router.get("/me", response_model=CustomerAuthResponse)
async def get_customer_profile(
    current_customer: Customer = Depends(get_current_customer)
):
    """Get current authenticated customer profile"""
    return current_customer


@router.get("/my-salons")
async def get_customer_salons(
    current_customer: Customer = Depends(get_current_customer),
    db: Session = Depends(get_db)
):
    """
    Get all salons the customer has interacted with (booked or purchased from).
    """
    salon_customers = db.query(SalonCustomer).filter(
        SalonCustomer.customer_id == current_customer.id
    ).all()
    
    result = []
    for sc in salon_customers:
        result.append({
            "salon_id": sc.salon_id,
            "salon_name": sc.salon.name if sc.salon else None,
            "salon_slug": sc.salon.slug if sc.salon else None,
            "source": sc.source,
            "total_spent": sc.total_spent,
            "total_appointments": sc.total_appointments,
            "first_interaction_at": sc.first_interaction_at,
            "last_interaction_at": sc.last_interaction_at
        })
    
    return {"salons": result, "total": len(result)}
