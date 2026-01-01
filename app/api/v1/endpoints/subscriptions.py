"""
API endpoints for subscription management
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_superadmin
from app.core.subscription_manager import (
    check_and_process_expired_subscriptions,
    get_subscription_status
)
from app.models.models import User, Salon

router = APIRouter()


@router.post("/process-expired")
def process_expired_subscriptions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superadmin)
):
    """
    Process all expired subscriptions (superadmin only)
    - Charge cards with auto_debit enabled
    - Downgrade to free plan if auto_debit disabled or charge fails
    
    This endpoint should be called by a cron job daily
    """
    try:
        results = check_and_process_expired_subscriptions(db)
        return {
            "status": "success",
            "message": "Processed expired subscriptions",
            "results": results
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing subscriptions: {str(e)}"
        )


@router.get("/status/{salon_id}")
def get_salon_subscription_status(
    salon_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superadmin)
):
    """
    Get subscription status for a specific salon (superadmin only)
    """
    salon = db.query(Salon).filter(Salon.id == salon_id).first()
    
    if not salon:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Salon not found"
        )
    
    status_info = get_subscription_status(salon)
    
    return {
        "salon_id": salon_id,
        "salon_name": salon.name,
        **status_info
    }
