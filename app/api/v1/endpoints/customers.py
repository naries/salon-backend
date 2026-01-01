from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_
from typing import List, Optional
from pydantic import BaseModel
from app.core.database import get_db
from app.core.security import get_current_admin_user
from app.models.models import Customer, User, ActivityLog, Salon, SalonCustomer

router = APIRouter()


class CustomerCreate(BaseModel):
    name: str
    email: str
    phone: Optional[str] = None
    salon_id: Optional[int] = None  # Required for superadmin


@router.get("/")
async def get_customers(
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Get customers with pagination and filtering
    - Superadmin: sees all platform customers
    - Salon admin: sees customers who have interacted with their salon (via SalonCustomer)
    """
    if current_user.is_superadmin == 1:
        # Superadmin sees all platform customers
        query = db.query(Customer).options(joinedload(Customer.salon))
        
        # Apply search filter
        if search:
            query = query.filter(
                or_(
                    Customer.name.ilike(f"%{search}%"),
                    Customer.email.ilike(f"%{search}%"),
                    Customer.phone.ilike(f"%{search}%")
                )
            )
        
        # Get total count
        total = query.count()
        
        # Apply pagination and ordering
        customers = query.order_by(Customer.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()
        
        return {
            "customers": customers,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": (total + per_page - 1) // per_page
        }
    else:
        # Salon admin sees customers via SalonCustomer relationship
        # This includes customers who have booked or purchased from their salon
        query = db.query(SalonCustomer).filter(
            SalonCustomer.salon_id == current_user.salon_id
        ).options(joinedload(SalonCustomer.customer))
        
        # Apply search filter on customer fields
        if search:
            query = query.join(Customer).filter(
                or_(
                    Customer.name.ilike(f"%{search}%"),
                    Customer.email.ilike(f"%{search}%"),
                    Customer.phone.ilike(f"%{search}%")
                )
            )
        
        # Get total count
        total = query.count()
        
        # Apply pagination and ordering
        salon_customers = query.order_by(SalonCustomer.last_interaction_at.desc()).offset((page - 1) * per_page).limit(per_page).all()
        
        # Format response to include both customer data and salon-specific data
        customers_data = []
        for sc in salon_customers:
            customer = sc.customer
            customers_data.append({
                "id": customer.id,
                "name": customer.name,
                "email": customer.email,
                "phone": customer.phone,
                "created_at": customer.created_at,
                # Salon-specific data from SalonCustomer
                "salon_customer_id": sc.id,
                "source": sc.source,
                "total_spent": sc.total_spent,
                "total_appointments": sc.total_appointments,
                "loyalty_points": sc.loyalty_points,
                "is_favorite": sc.is_favorite,
                "notes": sc.notes,
                "first_interaction_at": sc.first_interaction_at,
                "last_interaction_at": sc.last_interaction_at
            })
        
        return {
            "customers": customers_data,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": (total + per_page - 1) // per_page
        }


@router.post("/")
async def create_customer(
    customer_data: CustomerCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Create a new customer"""
    # Determine salon_id
    if current_user.is_superadmin == 1:
        if not customer_data.salon_id:
            raise HTTPException(status_code=400, detail="salon_id is required for superadmin")
        salon_id = customer_data.salon_id
    else:
        salon_id = current_user.salon_id
    
    # Check if customer already exists
    existing = db.query(Customer).filter(
        Customer.email == customer_data.email,
        Customer.salon_id == salon_id
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Customer with this email already exists")
    
    customer = Customer(
        name=customer_data.name,
        email=customer_data.email,
        phone=customer_data.phone,
        salon_id=salon_id
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)
    
    # Log customer creation
    log = ActivityLog(
        user_id=current_user.id,
        salon_id=salon_id,
        action="created",
        entity_type="customer",
        entity_id=customer.id,
        description=f"Created customer {customer.name} ({customer.email})",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    db.add(log)
    db.commit()
    
    return customer


@router.get("/{customer_id}")
def get_customer(customer_id: int, db: Session = Depends(get_db)):
    """Get customer by ID"""
    return {"customer_id": customer_id}


@router.put("/{customer_id}")
async def update_customer(
    customer_id: int,
    customer_data: CustomerCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Update a customer"""
    customer = db.query(Customer).filter(
        Customer.id == customer_id,
        Customer.salon_id == current_user.salon_id
    ).first()
    
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    # Check if email already exists for another customer
    if customer_data.email != customer.email:
        existing = db.query(Customer).filter(
            Customer.email == customer_data.email,
            Customer.salon_id == current_user.salon_id,
            Customer.id != customer_id
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="Customer with this email already exists")
    
    customer.name = customer_data.name
    customer.email = customer_data.email
    customer.phone = customer_data.phone
    
    db.commit()
    db.refresh(customer)
    
    # Log customer update
    log = ActivityLog(
        user_id=current_user.id,
        salon_id=current_user.salon_id,
        action="updated",
        entity_type="customer",
        entity_id=customer.id,
        description=f"Updated customer {customer.name} ({customer.email})",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    db.add(log)
    db.commit()
    
    return customer


@router.delete("/{customer_id}")
async def delete_customer(
    customer_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Delete a customer"""
    customer = db.query(Customer).filter(
        Customer.id == customer_id,
        Customer.salon_id == current_user.salon_id
    ).first()
    
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    customer_name = customer.name
    customer_email = customer.email
    
    db.delete(customer)
    db.commit()
    
    # Log customer deletion
    log = ActivityLog(
        user_id=current_user.id,
        salon_id=current_user.salon_id,
        action="deleted",
        entity_type="customer",
        entity_id=customer_id,
        description=f"Deleted customer {customer_name} ({customer_email})",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    db.add(log)
    db.commit()
    
    return {"message": "Customer deleted"}
