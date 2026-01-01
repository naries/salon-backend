"""
FAQ API Endpoints

Handles:
- Public FAQ retrieval
- Superadmin FAQ management (CRUD)
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import asc
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel

from app.core.database import get_db
from app.core.security import get_current_admin_user
from app.models.models import FAQ, User

router = APIRouter()


# Pydantic schemas
class FAQBase(BaseModel):
    question: str
    answer: str
    category: Optional[str] = None
    order_index: Optional[int] = 0


class FAQCreate(FAQBase):
    pass


class FAQUpdate(BaseModel):
    question: Optional[str] = None
    answer: Optional[str] = None
    category: Optional[str] = None
    order_index: Optional[int] = None
    is_active: Optional[int] = None


class FAQResponse(FAQBase):
    id: int
    is_active: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ==================== PUBLIC ENDPOINTS ====================

@router.get("/", response_model=List[FAQResponse])
def get_faqs(
    category: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get all active FAQs. Public endpoint for mobile app and website.
    """
    query = db.query(FAQ).filter(FAQ.is_active == 1)
    
    if category:
        query = query.filter(FAQ.category == category)
    
    faqs = query.order_by(asc(FAQ.order_index), asc(FAQ.id)).all()
    return faqs


@router.get("/categories")
def get_faq_categories(db: Session = Depends(get_db)):
    """
    Get unique FAQ categories.
    """
    categories = db.query(FAQ.category).filter(
        FAQ.is_active == 1,
        FAQ.category.isnot(None)
    ).distinct().all()
    
    return {"categories": [c[0] for c in categories if c[0]]}


# ==================== SUPERADMIN ENDPOINTS ====================

@router.get("/admin", response_model=List[FAQResponse])
def get_all_faqs_admin(
    include_inactive: bool = True,
    category: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Get all FAQs for admin management (superadmin only).
    """
    if not current_user.is_superadmin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superadmin can access this endpoint"
        )
    
    query = db.query(FAQ)
    
    if not include_inactive:
        query = query.filter(FAQ.is_active == 1)
    
    if category:
        query = query.filter(FAQ.category == category)
    
    faqs = query.order_by(asc(FAQ.order_index), asc(FAQ.id)).all()
    return faqs


@router.post("/admin", response_model=FAQResponse, status_code=status.HTTP_201_CREATED)
def create_faq(
    faq_data: FAQCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Create a new FAQ (superadmin only).
    """
    if not current_user.is_superadmin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superadmin can create FAQs"
        )
    
    faq = FAQ(
        question=faq_data.question,
        answer=faq_data.answer,
        category=faq_data.category,
        order_index=faq_data.order_index or 0
    )
    
    db.add(faq)
    db.commit()
    db.refresh(faq)
    
    return faq


@router.get("/admin/{faq_id}", response_model=FAQResponse)
def get_faq_admin(
    faq_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Get a specific FAQ by ID (superadmin only).
    """
    if not current_user.is_superadmin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superadmin can access this endpoint"
        )
    
    faq = db.query(FAQ).filter(FAQ.id == faq_id).first()
    if not faq:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="FAQ not found"
        )
    
    return faq


@router.put("/admin/{faq_id}", response_model=FAQResponse)
def update_faq(
    faq_id: int,
    faq_data: FAQUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Update an FAQ (superadmin only).
    """
    if not current_user.is_superadmin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superadmin can update FAQs"
        )
    
    faq = db.query(FAQ).filter(FAQ.id == faq_id).first()
    if not faq:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="FAQ not found"
        )
    
    # Update fields
    if faq_data.question is not None:
        faq.question = faq_data.question
    if faq_data.answer is not None:
        faq.answer = faq_data.answer
    if faq_data.category is not None:
        faq.category = faq_data.category
    if faq_data.order_index is not None:
        faq.order_index = faq_data.order_index
    if faq_data.is_active is not None:
        faq.is_active = faq_data.is_active
    
    faq.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(faq)
    
    return faq


@router.delete("/admin/{faq_id}")
def delete_faq(
    faq_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Delete an FAQ (superadmin only).
    """
    if not current_user.is_superadmin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superadmin can delete FAQs"
        )
    
    faq = db.query(FAQ).filter(FAQ.id == faq_id).first()
    if not faq:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="FAQ not found"
        )
    
    db.delete(faq)
    db.commit()
    
    return {"message": "FAQ deleted successfully"}
