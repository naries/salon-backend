from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from typing import List, Optional
from datetime import datetime
from app.core.database import get_db
from app.core.security import get_current_admin_user
from app.models.models import SupportTicket, User, Salon
from app.schemas.schemas import (
    SupportTicketCreate,
    SupportTicketUpdate,
    SupportTicketResponse
)

router = APIRouter()


@router.post("/", response_model=SupportTicketResponse, status_code=status.HTTP_201_CREATED)
def create_support_ticket(
    ticket_data: SupportTicketCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Create a new support ticket (salon admin only)"""
    if not current_user.salon_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must be associated with a salon"
        )
    
    ticket = SupportTicket(
        salon_id=current_user.salon_id,
        created_by=current_user.id,
        subject=ticket_data.subject,
        message=ticket_data.message,
        category=ticket_data.category,
        priority=ticket_data.priority or "normal",
        status="open"
    )
    
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    
    return ticket


@router.get("/", response_model=List[SupportTicketResponse])
def get_my_support_tickets(
    status_filter: Optional[str] = None,
    priority_filter: Optional[str] = None,
    category_filter: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Get all support tickets for the current salon"""
    if not current_user.salon_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must be associated with a salon"
        )
    
    query = db.query(SupportTicket).filter(
        SupportTicket.salon_id == current_user.salon_id
    )
    
    # Apply filters
    if status_filter:
        query = query.filter(SupportTicket.status == status_filter)
    if priority_filter:
        query = query.filter(SupportTicket.priority == priority_filter)
    if category_filter:
        query = query.filter(SupportTicket.category == category_filter)
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                SupportTicket.subject.ilike(search_term),
                SupportTicket.message.ilike(search_term)
            )
        )
    
    tickets = query.order_by(SupportTicket.created_at.desc()).all()
    return tickets


@router.get("/{ticket_id}", response_model=SupportTicketResponse)
def get_support_ticket(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Get a specific support ticket"""
    ticket = db.query(SupportTicket).filter(
        SupportTicket.id == ticket_id,
        SupportTicket.salon_id == current_user.salon_id
    ).first()
    
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Support ticket not found"
        )
    
    return ticket


@router.patch("/{ticket_id}", response_model=SupportTicketResponse)
def update_support_ticket(
    ticket_id: int,
    ticket_data: SupportTicketUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Update a support ticket (salon can only update status to closed)"""
    ticket = db.query(SupportTicket).filter(
        SupportTicket.id == ticket_id,
        SupportTicket.salon_id == current_user.salon_id
    ).first()
    
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Support ticket not found"
        )
    
    # Salon can only close their own tickets
    if ticket_data.status and ticket_data.status == "closed":
        ticket.status = "closed"
        ticket.resolved_at = datetime.utcnow()
    
    db.commit()
    db.refresh(ticket)
    return ticket
