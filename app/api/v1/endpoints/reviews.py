from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from datetime import datetime
from app.core.database import get_db
from app.core.security import get_current_admin_user
from app.models.models import Review, Salon, Customer
from app.schemas.schemas import (
    ReviewCreate, ReviewUpdate, ReviewResponse, 
    ReviewSalonResponse, SalonRatingSummary
)

router = APIRouter()


# Public endpoints (for salon customers)
@router.get("/salon/{salon_id}", response_model=List[ReviewResponse])
def get_salon_reviews(
    salon_id: int,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Get all visible reviews for a salon (public endpoint)"""
    # Verify salon exists
    salon = db.query(Salon).filter(Salon.id == salon_id, Salon.is_active == 1).first()
    if not salon:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Salon not found"
        )
    
    reviews = db.query(Review).filter(
        Review.salon_id == salon_id,
        Review.is_approved == 1,
        Review.is_visible == 1
    ).order_by(Review.created_at.desc()).offset(skip).limit(limit).all()
    
    return reviews


@router.get("/salon/{salon_id}/summary", response_model=SalonRatingSummary)
def get_salon_rating_summary(
    salon_id: int,
    db: Session = Depends(get_db)
):
    """Get rating summary for a salon (public endpoint)"""
    # Verify salon exists
    salon = db.query(Salon).filter(Salon.id == salon_id, Salon.is_active == 1).first()
    if not salon:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Salon not found"
        )
    
    # Get visible, approved reviews
    reviews = db.query(Review).filter(
        Review.salon_id == salon_id,
        Review.is_approved == 1,
        Review.is_visible == 1
    ).all()
    
    if not reviews:
        return SalonRatingSummary(
            average_rating=0.0,
            total_reviews=0,
            rating_distribution={"5": 0, "4": 0, "3": 0, "2": 0, "1": 0}
        )
    
    # Calculate average and distribution
    total = len(reviews)
    sum_ratings = sum(r.rating for r in reviews)
    average = round(sum_ratings / total, 1) if total > 0 else 0.0
    
    distribution = {"5": 0, "4": 0, "3": 0, "2": 0, "1": 0}
    for r in reviews:
        distribution[str(r.rating)] += 1
    
    return SalonRatingSummary(
        average_rating=average,
        total_reviews=total,
        rating_distribution=distribution
    )


@router.post("/", response_model=ReviewResponse, status_code=status.HTTP_201_CREATED)
def create_review(
    review_data: ReviewCreate,
    customer_id: Optional[int] = None,
    customer_name: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Create a new review for a salon.
    This is a public endpoint - customer info is passed as query params or from auth.
    """
    # Verify salon exists
    salon = db.query(Salon).filter(Salon.id == review_data.salon_id, Salon.is_active == 1).first()
    if not salon:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Salon not found"
        )
    
    # Validate rating
    if review_data.rating < 1 or review_data.rating > 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Rating must be between 1 and 5"
        )
    
    # If customer_id is provided, get customer info
    resolved_customer_name = customer_name or "Anonymous"
    if customer_id:
        customer = db.query(Customer).filter(Customer.id == customer_id).first()
        if customer:
            resolved_customer_name = customer.name
            
            # Check if customer already reviewed this salon
            existing_review = db.query(Review).filter(
                Review.salon_id == review_data.salon_id,
                Review.customer_id == customer_id
            ).first()
            if existing_review:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="You have already reviewed this salon. You can update your existing review."
                )
    
    # Create review
    db_review = Review(
        salon_id=review_data.salon_id,
        customer_id=customer_id,
        customer_name=resolved_customer_name,
        rating=review_data.rating,
        comment=review_data.comment,
        is_approved=1,  # Auto-approve by default
        is_visible=1
    )
    
    db.add(db_review)
    db.commit()
    db.refresh(db_review)
    
    return db_review


@router.post("/authenticated", response_model=ReviewResponse, status_code=status.HTTP_201_CREATED)
def create_authenticated_review(
    review_data: ReviewCreate,
    customer_id: int,
    customer_name: str,
    db: Session = Depends(get_db)
):
    """
    Create a review from an authenticated customer.
    customer_id and customer_name are passed from the customer auth middleware.
    """
    # Verify salon exists
    salon = db.query(Salon).filter(Salon.id == review_data.salon_id, Salon.is_active == 1).first()
    if not salon:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Salon not found"
        )
    
    # Validate rating
    if review_data.rating < 1 or review_data.rating > 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Rating must be between 1 and 5"
        )
    
    # Check if customer already reviewed this salon
    existing_review = db.query(Review).filter(
        Review.salon_id == review_data.salon_id,
        Review.customer_id == customer_id
    ).first()
    if existing_review:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You have already reviewed this salon. You can update your existing review."
        )
    
    # Create review
    db_review = Review(
        salon_id=review_data.salon_id,
        customer_id=customer_id,
        customer_name=customer_name,
        rating=review_data.rating,
        comment=review_data.comment,
        is_approved=1,
        is_visible=1
    )
    
    db.add(db_review)
    db.commit()
    db.refresh(db_review)
    
    return db_review


@router.put("/my-review/{salon_id}", response_model=ReviewResponse)
def update_my_review(
    salon_id: int,
    review_update: ReviewUpdate,
    customer_id: int,
    db: Session = Depends(get_db)
):
    """Update customer's own review for a salon"""
    review = db.query(Review).filter(
        Review.salon_id == salon_id,
        Review.customer_id == customer_id
    ).first()
    
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found"
        )
    
    # Validate rating if provided
    if review_update.rating is not None:
        if review_update.rating < 1 or review_update.rating > 5:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Rating must be between 1 and 5"
            )
        review.rating = review_update.rating
    
    if review_update.comment is not None:
        review.comment = review_update.comment
    
    db.commit()
    db.refresh(review)
    
    return review


@router.get("/my-review/{salon_id}", response_model=Optional[ReviewResponse])
def get_my_review(
    salon_id: int,
    customer_id: int,
    db: Session = Depends(get_db)
):
    """Get customer's own review for a salon"""
    review = db.query(Review).filter(
        Review.salon_id == salon_id,
        Review.customer_id == customer_id
    ).first()
    
    return review


@router.delete("/my-review/{salon_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_my_review(
    salon_id: int,
    customer_id: int,
    db: Session = Depends(get_db)
):
    """Delete customer's own review for a salon"""
    review = db.query(Review).filter(
        Review.salon_id == salon_id,
        Review.customer_id == customer_id
    ).first()
    
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found"
        )
    
    db.delete(review)
    db.commit()
    
    return None


# Salon admin endpoints
@router.get("/admin/all", response_model=List[ReviewResponse])
def get_all_salon_reviews(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """Get all reviews for the salon (admin view - includes hidden reviews)"""
    if not current_user.salon_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No salon associated with this user"
        )
    
    reviews = db.query(Review).filter(
        Review.salon_id == current_user.salon_id
    ).order_by(Review.created_at.desc()).offset(skip).limit(limit).all()
    
    return reviews


@router.put("/admin/{review_id}/respond", response_model=ReviewResponse)
def respond_to_review(
    review_id: int,
    response_data: ReviewSalonResponse,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """Respond to a customer review (salon admin)"""
    if not current_user.salon_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No salon associated with this user"
        )
    
    review = db.query(Review).filter(
        Review.id == review_id,
        Review.salon_id == current_user.salon_id
    ).first()
    
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found"
        )
    
    review.salon_response = response_data.salon_response
    review.responded_at = datetime.utcnow()
    
    db.commit()
    db.refresh(review)
    
    return review


@router.put("/admin/{review_id}/visibility", response_model=ReviewResponse)
def toggle_review_visibility(
    review_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """Toggle review visibility (salon admin can hide inappropriate reviews)"""
    if not current_user.salon_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No salon associated with this user"
        )
    
    review = db.query(Review).filter(
        Review.id == review_id,
        Review.salon_id == current_user.salon_id
    ).first()
    
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found"
        )
    
    review.is_visible = 0 if review.is_visible == 1 else 1
    
    db.commit()
    db.refresh(review)
    
    return review
