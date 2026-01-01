"""
Customer Support Messages API Endpoints

Handles:
- Customer message submission
- Customer message history
- Superadmin message management and responses
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel

from app.core.database import get_db
from app.core.security import get_current_admin_user, get_current_customer
from app.models.models import CustomerSupportMessage, Customer, User

router = APIRouter()


# Pydantic schemas
class SupportMessageCreate(BaseModel):
    subject: str
    message: str


class SupportMessageResponse(BaseModel):
    id: int
    customer_id: int
    subject: str
    message: str
    status: str
    admin_response: Optional[str] = None
    responded_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class SupportMessageWithCustomer(SupportMessageResponse):
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None


class AdminResponseCreate(BaseModel):
    response: str
    status: Optional[str] = "resolved"  # pending, in_progress, resolved


# ==================== CUSTOMER ENDPOINTS ====================

@router.post("/", response_model=SupportMessageResponse, status_code=status.HTTP_201_CREATED)
def create_support_message(
    message_data: SupportMessageCreate,
    db: Session = Depends(get_db),
    current_customer: Customer = Depends(get_current_customer)
):
    """
    Submit a support message (logged-in customers only).
    """
    message = CustomerSupportMessage(
        customer_id=current_customer.id,
        subject=message_data.subject,
        message=message_data.message,
        status="pending"
    )
    
    db.add(message)
    db.commit()
    db.refresh(message)
    
    return message


@router.get("/", response_model=List[SupportMessageResponse])
def get_my_support_messages(
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db),
    current_customer: Customer = Depends(get_current_customer)
):
    """
    Get all support messages for the current customer.
    """
    query = db.query(CustomerSupportMessage).filter(
        CustomerSupportMessage.customer_id == current_customer.id
    )
    
    if status_filter:
        query = query.filter(CustomerSupportMessage.status == status_filter)
    
    messages = query.order_by(desc(CustomerSupportMessage.created_at)).all()
    return messages


@router.get("/{message_id}", response_model=SupportMessageResponse)
def get_support_message(
    message_id: int,
    db: Session = Depends(get_db),
    current_customer: Customer = Depends(get_current_customer)
):
    """
    Get a specific support message by ID.
    """
    message = db.query(CustomerSupportMessage).filter(
        CustomerSupportMessage.id == message_id,
        CustomerSupportMessage.customer_id == current_customer.id
    ).first()
    
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found"
        )
    
    return message


# ==================== SUPERADMIN ENDPOINTS ====================

@router.get("/admin/all", response_model=List[SupportMessageWithCustomer])
def get_all_support_messages_admin(
    status_filter: Optional[str] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Get all support messages (superadmin only).
    """
    if not current_user.is_superadmin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superadmin can access this endpoint"
        )
    
    query = db.query(CustomerSupportMessage).join(Customer)
    
    if status_filter:
        query = query.filter(CustomerSupportMessage.status == status_filter)
    
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (CustomerSupportMessage.subject.ilike(search_term)) |
            (CustomerSupportMessage.message.ilike(search_term)) |
            (Customer.name.ilike(search_term)) |
            (Customer.email.ilike(search_term))
        )
    
    # Get paginated results
    total = query.count()
    messages = query.order_by(desc(CustomerSupportMessage.created_at)).offset(
        (page - 1) * per_page
    ).limit(per_page).all()
    
    # Convert to response with customer info
    result = []
    for msg in messages:
        customer = db.query(Customer).filter(Customer.id == msg.customer_id).first()
        result.append(SupportMessageWithCustomer(
            id=msg.id,
            customer_id=msg.customer_id,
            subject=msg.subject,
            message=msg.message,
            status=msg.status,
            admin_response=msg.admin_response,
            responded_at=msg.responded_at,
            created_at=msg.created_at,
            updated_at=msg.updated_at,
            customer_name=customer.name if customer else None,
            customer_email=customer.email if customer else None
        ))
    
    return result


@router.get("/admin/stats")
def get_support_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Get support message statistics (superadmin only).
    """
    if not current_user.is_superadmin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superadmin can access this endpoint"
        )
    
    total = db.query(CustomerSupportMessage).count()
    pending = db.query(CustomerSupportMessage).filter(
        CustomerSupportMessage.status == "pending"
    ).count()
    in_progress = db.query(CustomerSupportMessage).filter(
        CustomerSupportMessage.status == "in_progress"
    ).count()
    resolved = db.query(CustomerSupportMessage).filter(
        CustomerSupportMessage.status == "resolved"
    ).count()
    
    return {
        "total": total,
        "pending": pending,
        "in_progress": in_progress,
        "resolved": resolved
    }


@router.get("/admin/{message_id}", response_model=SupportMessageWithCustomer)
def get_support_message_admin(
    message_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Get a specific support message (superadmin only).
    """
    if not current_user.is_superadmin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superadmin can access this endpoint"
        )
    
    msg = db.query(CustomerSupportMessage).filter(
        CustomerSupportMessage.id == message_id
    ).first()
    
    if not msg:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found"
        )
    
    customer = db.query(Customer).filter(Customer.id == msg.customer_id).first()
    
    return SupportMessageWithCustomer(
        id=msg.id,
        customer_id=msg.customer_id,
        subject=msg.subject,
        message=msg.message,
        status=msg.status,
        admin_response=msg.admin_response,
        responded_at=msg.responded_at,
        created_at=msg.created_at,
        updated_at=msg.updated_at,
        customer_name=customer.name if customer else None,
        customer_email=customer.email if customer else None
    )


@router.post("/admin/{message_id}/respond", response_model=SupportMessageWithCustomer)
def respond_to_message(
    message_id: int,
    response_data: AdminResponseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Respond to a support message (superadmin only).
    """
    if not current_user.is_superadmin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superadmin can respond to messages"
        )
    
    msg = db.query(CustomerSupportMessage).filter(
        CustomerSupportMessage.id == message_id
    ).first()
    
    if not msg:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found"
        )
    
    msg.admin_response = response_data.response
    msg.status = response_data.status
    msg.responded_at = datetime.utcnow()
    msg.responded_by = current_user.id
    msg.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(msg)
    
    customer = db.query(Customer).filter(Customer.id == msg.customer_id).first()
    
    return SupportMessageWithCustomer(
        id=msg.id,
        customer_id=msg.customer_id,
        subject=msg.subject,
        message=msg.message,
        status=msg.status,
        admin_response=msg.admin_response,
        responded_at=msg.responded_at,
        created_at=msg.created_at,
        updated_at=msg.updated_at,
        customer_name=customer.name if customer else None,
        customer_email=customer.email if customer else None
    )


@router.put("/admin/{message_id}/status")
def update_message_status(
    message_id: int,
    new_status: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Update message status (superadmin only).
    """
    if not current_user.is_superadmin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superadmin can update message status"
        )
    
    if new_status not in ["pending", "in_progress", "resolved"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid status. Must be: pending, in_progress, or resolved"
        )
    
    msg = db.query(CustomerSupportMessage).filter(
        CustomerSupportMessage.id == message_id
    ).first()
    
    if not msg:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found"
        )
    
    msg.status = new_status
    msg.updated_at = datetime.utcnow()
    db.commit()
    
    return {"message": "Status updated successfully", "new_status": new_status}
