from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List, Optional
from datetime import datetime
from app.core.database import get_db
from app.core.security import get_current_admin_user
from app.models.models import CustomerComplaint, User, Customer, Salon
from app.schemas.schemas import (
    CustomerComplaintCreate,
    CustomerComplaintUpdate,
    CustomerComplaintResponse
)

router = APIRouter()


@router.post("/", response_model=CustomerComplaintResponse, status_code=status.HTTP_201_CREATED)
def create_customer_complaint(
    complaint_data: CustomerComplaintCreate,
    db: Session = Depends(get_db)
):
    """Create a new customer complaint (public endpoint)"""
    # Verify salon exists
    salon = db.query(Salon).filter(Salon.id == complaint_data.salon_id).first()
    if not salon:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Salon not found"
        )
    
    # Check if customer exists by email
    customer_id = None
    if complaint_data.customer_email:
        customer = db.query(Customer).filter(
            Customer.email == complaint_data.customer_email
        ).first()
        if customer:
            customer_id = customer.id
    
    complaint = CustomerComplaint(
        salon_id=complaint_data.salon_id,
        customer_id=customer_id,
        customer_name=complaint_data.customer_name,
        customer_email=complaint_data.customer_email,
        customer_phone=complaint_data.customer_phone,
        subject=complaint_data.subject,
        message=complaint_data.message,
        category=complaint_data.category,
        priority=complaint_data.priority or "normal",
        status="open"
    )
    
    db.add(complaint)
    db.commit()
    db.refresh(complaint)
    
    return complaint


@router.get("/", response_model=List[CustomerComplaintResponse])
def get_customer_complaints(
    status_filter: Optional[str] = None,
    priority_filter: Optional[str] = None,
    category_filter: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Get all customer complaints for the current salon"""
    if not current_user.salon_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must be associated with a salon"
        )
    
    query = db.query(CustomerComplaint).filter(
        CustomerComplaint.salon_id == current_user.salon_id
    )
    
    # Apply filters
    if status_filter:
        query = query.filter(CustomerComplaint.status == status_filter)
    if priority_filter:
        query = query.filter(CustomerComplaint.priority == priority_filter)
    if category_filter:
        query = query.filter(CustomerComplaint.category == category_filter)
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                CustomerComplaint.subject.ilike(search_term),
                CustomerComplaint.message.ilike(search_term),
                CustomerComplaint.customer_name.ilike(search_term),
                CustomerComplaint.customer_email.ilike(search_term)
            )
        )
    
    complaints = query.order_by(CustomerComplaint.created_at.desc()).all()
    
    # Add responder names
    for complaint in complaints:
        if complaint.responded_by:
            responder = db.query(User).filter(User.id == complaint.responded_by).first()
            if responder:
                complaint.responder_name = responder.name
    
    return complaints


@router.get("/{complaint_id}", response_model=CustomerComplaintResponse)
def get_customer_complaint(
    complaint_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Get a specific customer complaint"""
    complaint = db.query(CustomerComplaint).filter(
        CustomerComplaint.id == complaint_id,
        CustomerComplaint.salon_id == current_user.salon_id
    ).first()
    
    if not complaint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Complaint not found"
        )
    
    # Add responder name
    if complaint.responded_by:
        responder = db.query(User).filter(User.id == complaint.responded_by).first()
        if responder:
            complaint.responder_name = responder.name
    
    return complaint


@router.patch("/{complaint_id}", response_model=CustomerComplaintResponse)
def update_customer_complaint(
    complaint_id: int,
    complaint_data: CustomerComplaintUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Update a customer complaint (salon admin only)"""
    complaint = db.query(CustomerComplaint).filter(
        CustomerComplaint.id == complaint_id,
        CustomerComplaint.salon_id == current_user.salon_id
    ).first()
    
    if not complaint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Complaint not found"
        )
    
    # Update fields
    if complaint_data.status is not None:
        complaint.status = complaint_data.status
        if complaint_data.status in ["resolved", "closed"]:
            complaint.resolved_at = datetime.utcnow()
    
    if complaint_data.priority is not None:
        complaint.priority = complaint_data.priority
    
    if complaint_data.salon_response is not None:
        complaint.salon_response = complaint_data.salon_response
        complaint.responded_by = current_user.id
        complaint.responded_at = datetime.utcnow()
    
    db.commit()
    db.refresh(complaint)
    
    # Add responder name
    complaint.responder_name = current_user.name
    
    return complaint
