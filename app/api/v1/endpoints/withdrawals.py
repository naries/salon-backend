from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from datetime import datetime
import uuid

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import User, BankAccount, Withdrawal, Wallet
from app.schemas.schemas import (
    BankAccountCreate,
    BankAccountUpdate,
    BankAccountResponse,
    WithdrawalCreate,
    WithdrawalResponse,
    WithdrawalWithDetails,
)

router = APIRouter()


# Bank Account Endpoints
@router.post("/bank-accounts", response_model=BankAccountResponse)
def create_bank_account(
    bank_account: BankAccountCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new bank account for the salon"""
    if current_user.role != "salon_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only salon admins can manage bank accounts",
        )

    # If this is set as default, unset other default accounts
    if bank_account.is_default == 1:
        db.query(BankAccount).filter(
            BankAccount.salon_id == current_user.salon_id,
            BankAccount.is_default == 1,
        ).update({"is_default": 0})

    new_bank_account = BankAccount(
        salon_id=current_user.salon_id,
        **bank_account.model_dump(),
    )
    db.add(new_bank_account)
    db.commit()
    db.refresh(new_bank_account)
    return new_bank_account


@router.get("/bank-accounts", response_model=List[BankAccountResponse])
def list_bank_accounts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all bank accounts for the salon"""
    if current_user.role != "salon_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only salon admins can view bank accounts",
        )

    accounts = (
        db.query(BankAccount)
        .filter(BankAccount.salon_id == current_user.salon_id)
        .order_by(BankAccount.is_default.desc(), BankAccount.created_at.desc())
        .all()
    )
    return accounts


@router.get("/bank-accounts/{account_id}", response_model=BankAccountResponse)
def get_bank_account(
    account_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific bank account"""
    if current_user.role != "salon_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only salon admins can view bank accounts",
        )

    account = (
        db.query(BankAccount)
        .filter(
            BankAccount.id == account_id,
            BankAccount.salon_id == current_user.salon_id,
        )
        .first()
    )

    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bank account not found",
        )

    return account


@router.put("/bank-accounts/{account_id}", response_model=BankAccountResponse)
def update_bank_account(
    account_id: int,
    bank_account_update: BankAccountUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a bank account"""
    if current_user.role != "salon_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only salon admins can update bank accounts",
        )

    account = (
        db.query(BankAccount)
        .filter(
            BankAccount.id == account_id,
            BankAccount.salon_id == current_user.salon_id,
        )
        .first()
    )

    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bank account not found",
        )

    # If setting as default, unset other defaults
    if bank_account_update.is_default == 1:
        db.query(BankAccount).filter(
            BankAccount.salon_id == current_user.salon_id,
            BankAccount.id != account_id,
            BankAccount.is_default == 1,
        ).update({"is_default": 0})

    update_data = bank_account_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(account, key, value)

    db.commit()
    db.refresh(account)
    return account


@router.delete("/bank-accounts/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_bank_account(
    account_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a bank account"""
    if current_user.role != "salon_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only salon admins can delete bank accounts",
        )

    account = (
        db.query(BankAccount)
        .filter(
            BankAccount.id == account_id,
            BankAccount.salon_id == current_user.salon_id,
        )
        .first()
    )

    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bank account not found",
        )

    # Check if there are any pending withdrawals using this account
    pending_withdrawals = (
        db.query(Withdrawal)
        .filter(
            Withdrawal.bank_account_id == account_id,
            Withdrawal.status.in_(["pending", "approved"]),
        )
        .count()
    )

    if pending_withdrawals > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete account with pending withdrawals",
        )

    db.delete(account)
    db.commit()
    return None


@router.put("/bank-accounts/{account_id}/set-default", response_model=BankAccountResponse)
def set_default_bank_account(
    account_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Set a bank account as the default"""
    if current_user.role != "salon_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only salon admins can manage bank accounts",
        )

    account = (
        db.query(BankAccount)
        .filter(
            BankAccount.id == account_id,
            BankAccount.salon_id == current_user.salon_id,
        )
        .first()
    )

    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bank account not found",
        )

    # Unset all other defaults
    db.query(BankAccount).filter(
        BankAccount.salon_id == current_user.salon_id,
        BankAccount.id != account_id,
    ).update({"is_default": 0})

    account.is_default = 1
    db.commit()
    db.refresh(account)
    return account


# Withdrawal Endpoints
@router.post("/withdrawals/request", response_model=WithdrawalResponse)
def request_withdrawal(
    withdrawal: WithdrawalCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Request a withdrawal from the salon wallet"""
    if current_user.role != "salon_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only salon admins can request withdrawals",
        )

    # Get the salon's wallet
    wallet = (
        db.query(Wallet)
        .filter(Wallet.salon_id == current_user.salon_id)
        .first()
    )

    if not wallet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wallet not found",
        )

    # Check if the bank account exists and belongs to the salon
    bank_account = (
        db.query(BankAccount)
        .filter(
            BankAccount.id == withdrawal.bank_account_id,
            BankAccount.salon_id == current_user.salon_id,
        )
        .first()
    )

    if not bank_account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bank account not found",
        )

    # Validate amount
    if withdrawal.amount <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Withdrawal amount must be greater than zero",
        )

    # Check if there's sufficient balance
    if wallet.balance < withdrawal.amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Insufficient balance. Available: ₦{wallet.balance / 100:.2f}",
        )

    # Generate unique reference
    reference = f"WD-{uuid.uuid4().hex[:12].upper()}"

    # Create withdrawal request
    new_withdrawal = Withdrawal(
        wallet_id=wallet.id,
        bank_account_id=withdrawal.bank_account_id,
        amount=withdrawal.amount,
        status="pending",
        reference=reference,
        notes=withdrawal.notes,
    )

    db.add(new_withdrawal)
    db.commit()
    db.refresh(new_withdrawal)
    return new_withdrawal


@router.get("/withdrawals", response_model=List[WithdrawalWithDetails])
def list_withdrawals(
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all withdrawals for the salon"""
    if current_user.role != "salon_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only salon admins can view withdrawals",
        )

    # Get wallet for the salon
    wallet = (
        db.query(Wallet)
        .filter(Wallet.salon_id == current_user.salon_id)
        .first()
    )

    if not wallet:
        return []

    query = (
        db.query(Withdrawal)
        .options(
            joinedload(Withdrawal.bank_account),
            joinedload(Withdrawal.processor),
        )
        .filter(Withdrawal.wallet_id == wallet.id)
    )

    if status_filter:
        query = query.filter(Withdrawal.status == status_filter)

    withdrawals = query.order_by(Withdrawal.created_at.desc()).all()

    # Build response with details
    result = []
    for w in withdrawals:
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
            "salon_id": current_user.salon_id,
            "salon_name": current_user.salon.salon_name if current_user.salon else None,
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
def get_withdrawal(
    withdrawal_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get details of a specific withdrawal"""
    if current_user.role != "salon_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only salon admins can view withdrawals",
        )

    # Get wallet for the salon
    wallet = (
        db.query(Wallet)
        .filter(Wallet.salon_id == current_user.salon_id)
        .first()
    )

    if not wallet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wallet not found",
        )

    withdrawal = (
        db.query(Withdrawal)
        .options(
            joinedload(Withdrawal.bank_account),
            joinedload(Withdrawal.processor),
        )
        .filter(
            Withdrawal.id == withdrawal_id,
            Withdrawal.wallet_id == wallet.id,
        )
        .first()
    )

    if not withdrawal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Withdrawal not found",
        )

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
        "salon_id": current_user.salon_id,
        "salon_name": current_user.salon.salon_name if current_user.salon else None,
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
