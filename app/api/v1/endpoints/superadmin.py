from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from typing import List, Optional
from datetime import datetime

from app.core.database import get_db
from app.core.security import get_current_superadmin
from app.models.models import Salon, User, Wallet, WalletTransaction, Order, Withdrawal, BankAccount, SupportTicket
from app.schemas.schemas import (
    SalonResponse,
    WalletWithSalon,
    WalletTransactionWithDetails,
    WithdrawalWithDetails,
    WithdrawalUpdate,
    SupportTicketResponse,
    SupportTicketUpdate,
)

router = APIRouter()


@router.get("/")
async def get_all_salons(
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    search: Optional[str] = None,
    status: Optional[str] = Query(None, regex="^(active|inactive|all)$"),
    current_user: User = Depends(get_current_superadmin),
    db: Session = Depends(get_db)
):
    """
    Get all salons with pagination and filters (superadmin only)
    """
    # Base query - exclude soft-deleted salons
    query = db.query(Salon).filter(Salon.deleted_at.is_(None))
    
    # Apply search filter
    if search:
        query = query.filter(
            or_(
                Salon.name.ilike(f"%{search}%"),
                Salon.email.ilike(f"%{search}%"),
                Salon.slug.ilike(f"%{search}%")
            )
        )
    
    # Apply status filter
    if status == "active":
        query = query.filter(Salon.is_active == 1)
    elif status == "inactive":
        query = query.filter(Salon.is_active == 0)
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    salons = query.offset((page - 1) * per_page).limit(per_page).all()
    
    # Convert to dict to avoid serialization issues
    salons_data = [
        {
            "id": s.id,
            "name": s.name,
            "slug": s.slug,
            "email": s.email,
            "phone": s.phone,
            "address": s.address,
            "plan_id": s.plan_id,
            "is_active": s.is_active,
            "created_at": s.created_at.isoformat() if s.created_at else None,
        }
        for s in salons
    ]
    
    return {
        "salons": salons_data,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page
    }


@router.get("/{salon_id}", response_model=SalonResponse)
async def get_salon_details(
    salon_id: int,
    current_user: User = Depends(get_current_superadmin),
    db: Session = Depends(get_db)
):
    """
    Get detailed salon information (superadmin only)
    """
    salon = db.query(Salon).filter(
        Salon.id == salon_id,
        Salon.deleted_at.is_(None)
    ).first()
    
    if not salon:
        raise HTTPException(status_code=404, detail="Salon not found")
    
    return salon


@router.patch("/{salon_id}/toggle-active")
async def toggle_salon_active_status(
    salon_id: int,
    current_user: User = Depends(get_current_superadmin),
    db: Session = Depends(get_db)
):
    """
    Toggle salon active/inactive status (superadmin only)
    """
    salon = db.query(Salon).filter(
        Salon.id == salon_id,
        Salon.deleted_at.is_(None)
    ).first()
    
    if not salon:
        raise HTTPException(status_code=404, detail="Salon not found")
    
    # Toggle status
    salon.is_active = 0 if salon.is_active == 1 else 1
    db.commit()
    db.refresh(salon)
    
    return {
        "message": f"Salon {'activated' if salon.is_active == 1 else 'deactivated'} successfully",
        "salon": salon
    }


@router.delete("/{salon_id}")
async def soft_delete_salon(
    salon_id: int,
    current_user: User = Depends(get_current_superadmin),
    db: Session = Depends(get_db)
):
    """
    Soft delete a salon (superadmin only)
    Sets deleted_at timestamp, salon becomes inaccessible
    """
    salon = db.query(Salon).filter(
        Salon.id == salon_id,
        Salon.deleted_at.is_(None)
    ).first()
    
    if not salon:
        raise HTTPException(status_code=404, detail="Salon not found")
    
    # Soft delete
    salon.deleted_at = datetime.utcnow()
    db.commit()
    
    return {
        "message": "Salon deleted successfully",
        "salon_id": salon_id
    }


@router.get("/wallets/all", response_model=List[WalletWithSalon])
async def get_all_wallets(
    salon_id: Optional[int] = Query(None, description="Filter by specific salon"),
    current_user: User = Depends(get_current_superadmin),
    db: Session = Depends(get_db)
):
    """
    Get all salon wallets with balances (superadmin only)
    """
    query = db.query(Wallet).join(Salon, Wallet.salon_id == Salon.id)
    
    if salon_id:
        query = query.filter(Wallet.salon_id == salon_id)
    
    wallets = query.all()
    
    # Add salon information to each wallet
    result = []
    for wallet in wallets:
        salon = db.query(Salon).filter(Salon.id == wallet.salon_id).first()
        result.append({
            "id": wallet.id,
            "salon_id": wallet.salon_id,
            "balance": wallet.balance,
            "created_at": wallet.created_at,
            "updated_at": wallet.updated_at,
            "salon_name": salon.name if salon else None,
            "salon_slug": salon.slug if salon else None
        })
    
    return result


@router.get("/wallets/transactions", response_model=List[WalletTransactionWithDetails])
async def get_all_wallet_transactions(
    salon_id: Optional[int] = Query(None, description="Filter by specific salon"),
    status_filter: Optional[str] = Query(None, description="Filter by status: pending, completed, failed"),
    type_filter: Optional[str] = Query(None, description="Filter by type: credit, debit"),
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_superadmin),
    db: Session = Depends(get_db)
):
    """
    Get all wallet transactions across all salons (superadmin only)
    """
    query = db.query(WalletTransaction).join(Wallet, WalletTransaction.wallet_id == Wallet.id)
    
    # Apply filters
    if salon_id:
        query = query.filter(Wallet.salon_id == salon_id)
    
    if status_filter:
        query = query.filter(WalletTransaction.status == status_filter)
    
    if type_filter:
        query = query.filter(WalletTransaction.type == type_filter)
    
    # Order by most recent first
    query = query.order_by(WalletTransaction.created_at.desc())
    
    # Apply pagination
    transactions = query.offset(offset).limit(limit).all()
    
    # Add salon and order information
    result = []
    for txn in transactions:
        wallet = db.query(Wallet).filter(Wallet.id == txn.wallet_id).first()
        salon = db.query(Salon).filter(Salon.id == wallet.salon_id).first() if wallet else None
        order = db.query(Order).filter(Order.id == txn.order_id).first() if txn.order_id else None
        
        result.append({
            "id": txn.id,
            "wallet_id": txn.wallet_id,
            "order_id": txn.order_id,
            "amount": txn.amount,
            "type": txn.type,
            "status": txn.status,
            "payment_reference": txn.payment_reference,
            "description": txn.description,
            "created_at": txn.created_at,
            "updated_at": txn.updated_at,
            "salon_id": wallet.salon_id if wallet else None,
            "salon_name": salon.name if salon else None,
            "order_number": order.order_number if order else None
        })
    
    return result


# Withdrawal Management Endpoints
@router.get("/withdrawals/all", response_model=List[WithdrawalWithDetails])
async def get_all_withdrawals(
    salon_id: Optional[int] = None,
    status_filter: Optional[str] = None,
    current_user: User = Depends(get_current_superadmin),
    db: Session = Depends(get_db)
):
    """
    Get all withdrawal requests from all salons (superadmin only)
    """
    from sqlalchemy.orm import joinedload
    
    query = db.query(Withdrawal).options(
        joinedload(Withdrawal.wallet).joinedload(Wallet.salon),
        joinedload(Withdrawal.bank_account),
        joinedload(Withdrawal.processor)
    )
    
    # Filter by salon if specified
    if salon_id:
        wallet_ids = db.query(Wallet.id).filter(Wallet.salon_id == salon_id).all()
        wallet_ids = [w[0] for w in wallet_ids]
        query = query.filter(Withdrawal.wallet_id.in_(wallet_ids))
    
    # Filter by status if specified
    if status_filter:
        query = query.filter(Withdrawal.status == status_filter)
    
    withdrawals = query.order_by(Withdrawal.created_at.desc()).all()
    
    # Build response with details
    result = []
    for w in withdrawals:
        salon = w.wallet.salon if w.wallet else None
        withdrawal_dict = {
            "id": w.id,
            "wallet_id": w.wallet_id,
            "bank_account_id": w.bank_account_id,
            "amount": w.amount,
            "status": w.status,
            "reference": w.reference,
            "notes": w.notes,
            "admin_notes": w.admin_notes,
            "transaction_reference": w.transaction_reference,
            "processed_by": w.processed_by,
            "processed_at": w.processed_at,
            "created_at": w.created_at,
            "updated_at": w.updated_at,
            "salon_id": salon.id if salon else None,
            "salon_name": salon.salon_name if salon else None,
            "bank_account": {
                "id": w.bank_account.id,
                "salon_id": w.bank_account.salon_id,
                "account_name": w.bank_account.account_name,
                "account_number": w.bank_account.account_number,
                "bank_name": w.bank_account.bank_name,
                "bank_code": w.bank_account.bank_code,
                "is_default": w.bank_account.is_default,
                "is_verified": w.bank_account.is_verified,
                "created_at": w.bank_account.created_at,
                "updated_at": w.bank_account.updated_at,
            } if w.bank_account else None,
            "processor_name": (
                f"{w.processor.first_name} {w.processor.last_name}"
                if w.processor else None
            ),
        }
        result.append(withdrawal_dict)
    
    return result


@router.get("/withdrawals/{withdrawal_id}", response_model=WithdrawalWithDetails)
async def get_withdrawal_details(
    withdrawal_id: int,
    current_user: User = Depends(get_current_superadmin),
    db: Session = Depends(get_db)
):
    """
    Get details of a specific withdrawal (superadmin only)
    """
    from sqlalchemy.orm import joinedload
    
    withdrawal = db.query(Withdrawal).options(
        joinedload(Withdrawal.wallet).joinedload(Wallet.salon),
        joinedload(Withdrawal.bank_account),
        joinedload(Withdrawal.processor)
    ).filter(Withdrawal.id == withdrawal_id).first()
    
    if not withdrawal:
        raise HTTPException(status_code=404, detail="Withdrawal not found")
    
    salon = withdrawal.wallet.salon if withdrawal.wallet else None
    
    return {
        "id": withdrawal.id,
        "wallet_id": withdrawal.wallet_id,
        "bank_account_id": withdrawal.bank_account_id,
        "amount": withdrawal.amount,
        "status": withdrawal.status,
        "reference": withdrawal.reference,
        "notes": withdrawal.notes,
        "admin_notes": withdrawal.admin_notes,
        "transaction_reference": withdrawal.transaction_reference,
        "processed_by": withdrawal.processed_by,
        "processed_at": withdrawal.processed_at,
        "created_at": withdrawal.created_at,
        "updated_at": withdrawal.updated_at,
        "salon_id": salon.id if salon else None,
        "salon_name": salon.salon_name if salon else None,
        "bank_account": {
            "id": withdrawal.bank_account.id,
            "salon_id": withdrawal.bank_account.salon_id,
            "account_name": withdrawal.bank_account.account_name,
            "account_number": withdrawal.bank_account.account_number,
            "bank_name": withdrawal.bank_account.bank_name,
            "bank_code": withdrawal.bank_account.bank_code,
            "is_default": withdrawal.bank_account.is_default,
            "is_verified": withdrawal.bank_account.is_verified,
            "created_at": withdrawal.bank_account.created_at,
            "updated_at": withdrawal.bank_account.updated_at,
        } if withdrawal.bank_account else None,
        "processor_name": (
            f"{withdrawal.processor.first_name} {withdrawal.processor.last_name}"
            if withdrawal.processor else None
        ),
    }


@router.post("/withdrawals/{withdrawal_id}/approve")
async def approve_withdrawal(
    withdrawal_id: int,
    admin_notes: Optional[str] = None,
    current_user: User = Depends(get_current_superadmin),
    db: Session = Depends(get_db)
):
    """
    Approve a withdrawal request (superadmin only)
    """
    withdrawal = db.query(Withdrawal).filter(Withdrawal.id == withdrawal_id).first()
    
    if not withdrawal:
        raise HTTPException(status_code=404, detail="Withdrawal not found")
    
    if withdrawal.status != "pending":
        raise HTTPException(
            status_code=400,
            detail=f"Cannot approve withdrawal with status: {withdrawal.status}"
        )
    
    # Update withdrawal status
    withdrawal.status = "approved"
    withdrawal.admin_notes = admin_notes
    withdrawal.processed_by = current_user.id
    withdrawal.processed_at = datetime.now()
    
    db.commit()
    db.refresh(withdrawal)
    
    return {
        "message": "Withdrawal approved successfully",
        "withdrawal_id": withdrawal.id,
        "reference": withdrawal.reference,
        "status": withdrawal.status
    }


@router.post("/withdrawals/{withdrawal_id}/reject")
async def reject_withdrawal(
    withdrawal_id: int,
    admin_notes: str,
    current_user: User = Depends(get_current_superadmin),
    db: Session = Depends(get_db)
):
    """
    Reject a withdrawal request (superadmin only)
    """
    withdrawal = db.query(Withdrawal).filter(Withdrawal.id == withdrawal_id).first()
    
    if not withdrawal:
        raise HTTPException(status_code=404, detail="Withdrawal not found")
    
    if withdrawal.status != "pending":
        raise HTTPException(
            status_code=400,
            detail=f"Cannot reject withdrawal with status: {withdrawal.status}"
        )
    
    if not admin_notes:
        raise HTTPException(
            status_code=400,
            detail="Rejection reason (admin_notes) is required"
        )
    
    # Update withdrawal status
    withdrawal.status = "rejected"
    withdrawal.admin_notes = admin_notes
    withdrawal.processed_by = current_user.id
    withdrawal.processed_at = datetime.now()
    
    db.commit()
    db.refresh(withdrawal)
    
    return {
        "message": "Withdrawal rejected",
        "withdrawal_id": withdrawal.id,
        "reference": withdrawal.reference,
        "status": withdrawal.status
    }


@router.put("/withdrawals/{withdrawal_id}/complete")
async def complete_withdrawal(
    withdrawal_id: int,
    transaction_reference: str,
    admin_notes: Optional[str] = None,
    current_user: User = Depends(get_current_superadmin),
    db: Session = Depends(get_db)
):
    """
    Mark a withdrawal as completed with payment gateway transaction reference (superadmin only)
    """
    from sqlalchemy.orm import joinedload
    
    withdrawal = db.query(Withdrawal).options(
        joinedload(Withdrawal.wallet)
    ).filter(Withdrawal.id == withdrawal_id).first()
    
    if not withdrawal:
        raise HTTPException(status_code=404, detail="Withdrawal not found")
    
    if withdrawal.status != "approved":
        raise HTTPException(
            status_code=400,
            detail=f"Can only complete approved withdrawals. Current status: {withdrawal.status}"
        )
    
    if not transaction_reference:
        raise HTTPException(
            status_code=400,
            detail="Transaction reference is required to complete withdrawal"
        )
    
    # Update withdrawal status
    withdrawal.status = "completed"
    withdrawal.transaction_reference = transaction_reference
    if admin_notes:
        withdrawal.admin_notes = admin_notes
    withdrawal.processed_at = datetime.now()
    
    # Deduct amount from wallet balance
    wallet = withdrawal.wallet
    if wallet:
        wallet.balance -= withdrawal.amount
    
    db.commit()
    db.refresh(withdrawal)
    
    return {
        "message": "Withdrawal completed successfully",
        "withdrawal_id": withdrawal.id,
        "reference": withdrawal.reference,
        "transaction_reference": withdrawal.transaction_reference,
        "status": withdrawal.status,
        "amount": withdrawal.amount
    }


@router.put("/withdrawals/{withdrawal_id}/fail")
async def fail_withdrawal(
    withdrawal_id: int,
    admin_notes: str,
    current_user: User = Depends(get_current_superadmin),
    db: Session = Depends(get_db)
):
    """
    Mark a withdrawal as failed (superadmin only)
    """
    withdrawal = db.query(Withdrawal).filter(Withdrawal.id == withdrawal_id).first()
    
    if not withdrawal:
        raise HTTPException(status_code=404, detail="Withdrawal not found")
    
    if withdrawal.status not in ["approved", "pending"]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot fail withdrawal with status: {withdrawal.status}"
        )
    
    if not admin_notes:
        raise HTTPException(
            status_code=400,
            detail="Failure reason (admin_notes) is required"
        )
    
    # Update withdrawal status
    withdrawal.status = "failed"
    withdrawal.admin_notes = admin_notes
    withdrawal.processed_by = current_user.id
    withdrawal.processed_at = datetime.now()
    
    return {
        "message": "Withdrawal marked as failed",
        "withdrawal_id": withdrawal.id,
        "reference": withdrawal.reference,
        "status": withdrawal.status
    }


@router.get("/orders")
async def get_all_orders(
    status: Optional[str] = None,
    search: Optional[str] = None,
    salon_id: Optional[int] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_superadmin),
    db: Session = Depends(get_db)
):
    """
    Get all orders across all salons with filters (superadmin only)
    """
    query = db.query(Order)
    
    # Apply filters
    if status:
        query = query.filter(Order.status == status)
    
    if salon_id:
        query = query.filter(Order.salon_id == salon_id)
    
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (Order.order_number.ilike(search_term)) |
            (Order.customer_name.ilike(search_term)) |
            (Order.customer_email.ilike(search_term)) |
            (Order.customer_phone.ilike(search_term))
        )
    
    if start_date:
        try:
            start = datetime.fromisoformat(start_date)
            query = query.filter(Order.created_at >= start)
        except ValueError:
            pass
    
    if end_date:
        try:
            end = datetime.fromisoformat(end_date)
            query = query.filter(Order.created_at <= end)
        except ValueError:
            pass
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    orders = query.order_by(Order.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()
    
    # Format response with salon info
    orders_with_salon = []
    for order in orders:
        order_dict = {
            "id": order.id,
            "order_number": order.order_number,
            "salon_id": order.salon_id,
            "salon_name": order.salon.name if order.salon else None,
            "salon_slug": order.salon.slug if order.salon else None,
            "customer_id": order.customer_id,
            "customer_name": order.customer_name or (order.customer.name if order.customer else None),
            "customer_email": order.customer_email or (order.customer.email if order.customer else None),
            "customer_phone": order.customer_phone or (order.customer.phone if order.customer else None),
            "total_amount": order.total_amount,
            "status": order.status,
            "payment_method": order.payment_method,
            "payment_reference": order.payment_reference,
            "delivery_address": order.delivery_address,
            "city": order.city,
            "notes": order.notes,
            "created_at": order.created_at.isoformat() if order.created_at else None,
            "updated_at": order.updated_at.isoformat() if order.updated_at else None,
            "items": [
                {
                    "id": item.id,
                    "product_id": item.product_id,
                    "product_name": item.product.name if item.product else None,
                    "pack_id": item.pack_id,
                    "pack_name": item.pack.name if item.pack else None,
                    "quantity": item.quantity,
                    "price_at_purchase": item.price_at_purchase
                }
                for item in order.items
            ]
        }
        orders_with_salon.append(order_dict)
    
    return {
        "total": total,
        "page": page,
        "per_page": per_page,
        "orders": orders_with_salon
    }


@router.get("/orders/{order_id}")
async def get_order_details(
    order_id: int,
    current_user: User = Depends(get_current_superadmin),
    db: Session = Depends(get_db)
):
    """
    Get specific order details (superadmin only)
    """
    order = db.query(Order).filter(Order.id == order_id).first()
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    return {
        "id": order.id,
        "order_number": order.order_number,
        "salon_id": order.salon_id,
        "salon_name": order.salon.name if order.salon else None,
        "salon_slug": order.salon.slug if order.salon else None,
        "customer_id": order.customer_id,
        "customer_name": order.customer_name or (order.customer.name if order.customer else None),
        "customer_email": order.customer_email or (order.customer.email if order.customer else None),
        "customer_phone": order.customer_phone or (order.customer.phone if order.customer else None),
        "total_amount": order.total_amount,
        "status": order.status,
        "payment_method": order.payment_method,
        "payment_reference": order.payment_reference,
        "delivery_address": order.delivery_address,
        "city": order.city,
        "notes": order.notes,
        "created_at": order.created_at.isoformat() if order.created_at else None,
        "updated_at": order.updated_at.isoformat() if order.updated_at else None,
        "items": [
            {
                "id": item.id,
                "product_id": item.product_id,
                "product_name": item.product.name if item.product else None,
                "pack_id": item.pack_id,
                "pack_name": item.pack.name if item.pack else None,
                "quantity": item.quantity,
                "price_at_purchase": item.price_at_purchase
            }
            for item in order.items
        ]
    }


# Support Tickets (Superadmin)
@router.get("/support-tickets", response_model=List[SupportTicketResponse])
def get_all_support_tickets(
    status_filter: Optional[str] = None,
    priority_filter: Optional[str] = None,
    category_filter: Optional[str] = None,
    salon_id: Optional[int] = None,
    search: Optional[str] = None,
    page: int = 1,
    per_page: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superadmin)
):
    """Get all support tickets from all salons (superadmin only)"""
    query = db.query(SupportTicket)
    
    # Apply filters
    if status_filter:
        query = query.filter(SupportTicket.status == status_filter)
    if priority_filter:
        query = query.filter(SupportTicket.priority == priority_filter)
    if category_filter:
        query = query.filter(SupportTicket.category == category_filter)
    if salon_id:
        query = query.filter(SupportTicket.salon_id == salon_id)
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                SupportTicket.subject.ilike(search_term),
                SupportTicket.message.ilike(search_term)
            )
        )
    
    # Pagination
    total = query.count()
    offset = (page - 1) * per_page
    tickets = query.order_by(SupportTicket.created_at.desc()).offset(offset).limit(per_page).all()
    
    # Add salon and creator names
    for ticket in tickets:
        salon = db.query(Salon).filter(Salon.id == ticket.salon_id).first()
        if salon:
            ticket.salon_name = salon.name
        
        if ticket.created_by:
            creator = db.query(User).filter(User.id == ticket.created_by).first()
            if creator:
                ticket.creator_name = creator.name
    
    return tickets


@router.get("/support-tickets/{ticket_id}", response_model=SupportTicketResponse)
def get_support_ticket_details(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superadmin)
):
    """Get detailed information about a specific support ticket"""
    ticket = db.query(SupportTicket).filter(SupportTicket.id == ticket_id).first()
    
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Support ticket not found"
        )
    
    # Add salon and creator names
    salon = db.query(Salon).filter(Salon.id == ticket.salon_id).first()
    if salon:
        ticket.salon_name = salon.name
    
    if ticket.created_by:
        creator = db.query(User).filter(User.id == ticket.created_by).first()
        if creator:
            ticket.creator_name = creator.name
    
    return ticket


@router.patch("/support-tickets/{ticket_id}", response_model=SupportTicketResponse)
def respond_to_support_ticket(
    ticket_id: int,
    ticket_data: SupportTicketUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superadmin)
):
    """Respond to a support ticket (superadmin only)"""
    ticket = db.query(SupportTicket).filter(SupportTicket.id == ticket_id).first()
    
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Support ticket not found"
        )
    
    # Update fields
    if ticket_data.status is not None:
        ticket.status = ticket_data.status
        if ticket_data.status in ["resolved", "closed"]:
            ticket.resolved_at = datetime.utcnow()
    
    if ticket_data.priority is not None:
        ticket.priority = ticket_data.priority
    
    if ticket_data.admin_response is not None:
        ticket.admin_response = ticket_data.admin_response
        ticket.responded_by = current_user.id
        ticket.responded_at = datetime.utcnow()
    
    db.commit()
    db.refresh(ticket)
    
    # Add salon name
    salon = db.query(Salon).filter(Salon.id == ticket.salon_id).first()
    if salon:
        ticket.salon_name = salon.name
    
    return ticket
