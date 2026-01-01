from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from typing import List, Optional
from datetime import datetime, timedelta
from app.core.database import get_db
from app.models.models import Wallet, WalletTransaction, Salon, Order
from app.schemas.schemas import WalletResponse, WalletTransactionResponse
from app.core.security import get_current_admin_user
from app.models.models import User

router = APIRouter()


@router.get("/", response_model=WalletResponse)
def get_wallet(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Get wallet for current salon."""
    if not current_user.salon_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not associated with a salon"
        )
    
    # Get or create wallet for salon
    wallet = db.query(Wallet).filter(Wallet.salon_id == current_user.salon_id).first()
    
    if not wallet:
        wallet = Wallet(salon_id=current_user.salon_id, balance=0)
        db.add(wallet)
        db.commit()
        db.refresh(wallet)
    
    return wallet


@router.get("/transactions", response_model=List[WalletTransactionResponse])
def get_wallet_transactions(
    status_filter: Optional[str] = Query(None, description="Filter by status: pending, completed, failed"),
    type_filter: Optional[str] = Query(None, description="Filter by type: credit, debit"),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Get transaction history for current salon wallet with filters."""
    if not current_user.salon_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not associated with a salon"
        )
    
    # Get wallet
    wallet = db.query(Wallet).filter(Wallet.salon_id == current_user.salon_id).first()
    
    if not wallet:
        return []
    
    # Build query
    query = db.query(WalletTransaction).filter(WalletTransaction.wallet_id == wallet.id)
    
    # Apply filters
    if status_filter:
        query = query.filter(WalletTransaction.status == status_filter)
    
    if type_filter:
        query = query.filter(WalletTransaction.type == type_filter)
    
    if start_date:
        try:
            start_dt = datetime.fromisoformat(start_date)
            query = query.filter(WalletTransaction.created_at >= start_dt)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid start_date format. Use YYYY-MM-DD"
            )
    
    if end_date:
        try:
            end_dt = datetime.fromisoformat(end_date) + timedelta(days=1)  # Include entire day
            query = query.filter(WalletTransaction.created_at < end_dt)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid end_date format. Use YYYY-MM-DD"
            )
    
    # Order by most recent first
    query = query.order_by(WalletTransaction.created_at.desc())
    
    # Apply pagination
    transactions = query.offset(offset).limit(limit).all()
    
    return transactions


@router.get("/transactions/{transaction_id}", response_model=WalletTransactionResponse)
def get_wallet_transaction(
    transaction_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Get specific transaction details."""
    if not current_user.salon_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not associated with a salon"
        )
    
    # Get wallet
    wallet = db.query(Wallet).filter(Wallet.salon_id == current_user.salon_id).first()
    
    if not wallet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wallet not found"
        )
    
    # Get transaction
    transaction = db.query(WalletTransaction).filter(
        WalletTransaction.id == transaction_id,
        WalletTransaction.wallet_id == wallet.id
    ).first()
    
    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found"
        )
    
    return transaction


@router.get("/balance", response_model=dict)
def get_wallet_balance(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Get current wallet balance."""
    if not current_user.salon_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not associated with a salon"
        )
    
    # Get or create wallet
    wallet = db.query(Wallet).filter(Wallet.salon_id == current_user.salon_id).first()
    
    if not wallet:
        wallet = Wallet(salon_id=current_user.salon_id, balance=0)
        db.add(wallet)
        db.commit()
        db.refresh(wallet)
    
    return {
        "balance": wallet.balance,
        "balance_formatted": f"₦{(wallet.balance / 100):.2f}"
    }
