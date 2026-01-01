from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
from datetime import datetime
from app.core.database import get_db
from app.core.security import get_current_superadmin
from app.models.models import Plan, User, ActivityLog
from app.schemas.schemas import PlanResponse, PlanCreate, PlanUpdate

router = APIRouter()


@router.get("/", response_model=List[PlanResponse])
def get_plans(
    include_deleted: bool = False,
    db: Session = Depends(get_db)
):
    """Get all plans (public endpoint). Superadmins can see deleted plans."""
    query = db.query(Plan).filter(Plan.is_active == 1)
    
    if include_deleted:
        query = db.query(Plan)  # Show all including soft deleted
    
    plans = query.all()
    return plans


@router.get("/all", response_model=List[PlanResponse])
def get_all_plans(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superadmin)
):
    """Get all plans including inactive/deleted (superadmin only)"""
    plans = db.query(Plan).all()
    return plans


@router.get("/{plan_id}", response_model=PlanResponse)
def get_plan(plan_id: int, db: Session = Depends(get_db)):
    """Get plan by ID"""
    plan = db.query(Plan).filter(Plan.id == plan_id).first()
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plan not found"
        )
    return plan


@router.post("/", response_model=PlanResponse, status_code=status.HTTP_201_CREATED)
def create_plan(
    plan_data: PlanCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superadmin)
):
    """Create a new plan (superadmin only)"""
    # Check if plan with same name exists (including soft deleted)
    existing_plan = db.query(Plan).filter(
        Plan.name == plan_data.name,
        Plan.deleted_at.is_(None)
    ).first()
    if existing_plan:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Plan with this name already exists"
        )
    
    db_plan = Plan(
        name=plan_data.name,
        description=plan_data.description,
        price=plan_data.price,
        monthly_price=plan_data.monthly_price,
        yearly_price=plan_data.yearly_price,
        discount_percentage=plan_data.discount_percentage or 0,
        features=plan_data.features,
        max_services=plan_data.max_services or 5,
        max_staff=plan_data.max_staff or 1,
        max_appointments_per_month=plan_data.max_appointments_per_month or 0,
        max_customers=plan_data.max_customers or 0,
        max_concurrent_slots=plan_data.max_concurrent_slots or 1,
        has_analytics=plan_data.has_analytics or 0,
        has_advanced_reporting=plan_data.has_advanced_reporting or 0,
        has_custom_branding=plan_data.has_custom_branding or 0,
        has_priority_support=plan_data.has_priority_support or 0
    )
    db.add(db_plan)
    db.commit()
    db.refresh(db_plan)
    
    # Log plan creation
    log = ActivityLog(
        user_id=current_user.id,
        salon_id=current_user.salon_id,
        action="created",
        entity_type="plan",
        entity_id=db_plan.id,
        description=f"Created plan {db_plan.name} (${db_plan.monthly_price}/month)",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    db.add(log)
    db.commit()
    
    return db_plan


@router.put("/{plan_id}", response_model=PlanResponse)
def update_plan(
    plan_id: int,
    plan_data: PlanUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superadmin)
):
    """Update plan pricing and details (superadmin only)"""
    plan = db.query(Plan).filter(
        Plan.id == plan_id,
        Plan.deleted_at.is_(None)
    ).first()
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plan not found"
        )
    
    # Prevent deactivating free plan if it's the only active plan
    if plan_data.is_active == 0:
        active_plans_count = db.query(func.count(Plan.id)).filter(
            Plan.is_active == 1,
            Plan.deleted_at.is_(None)
        ).scalar()
        
        if active_plans_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot deactivate the last active plan"
            )
    
    # Update fields if provided
    if plan_data.name is not None:
        plan.name = plan_data.name
    if plan_data.description is not None:
        plan.description = plan_data.description
    if plan_data.price is not None:
        plan.price = plan_data.price
    if plan_data.monthly_price is not None:
        plan.monthly_price = plan_data.monthly_price
    if plan_data.yearly_price is not None:
        plan.yearly_price = plan_data.yearly_price
    if plan_data.discount_percentage is not None:
        plan.discount_percentage = plan_data.discount_percentage
    if plan_data.features is not None:
        plan.features = plan_data.features
    if plan_data.max_services is not None:
        plan.max_services = plan_data.max_services
    if plan_data.max_staff is not None:
        plan.max_staff = plan_data.max_staff
    if plan_data.max_appointments_per_month is not None:
        plan.max_appointments_per_month = plan_data.max_appointments_per_month
    if plan_data.max_customers is not None:
        plan.max_customers = plan_data.max_customers
    if plan_data.max_concurrent_slots is not None:
        plan.max_concurrent_slots = plan_data.max_concurrent_slots
    if plan_data.has_analytics is not None:
        plan.has_analytics = plan_data.has_analytics
    if plan_data.has_advanced_reporting is not None:
        plan.has_advanced_reporting = plan_data.has_advanced_reporting
    if plan_data.has_custom_branding is not None:
        plan.has_custom_branding = plan_data.has_custom_branding
    if plan_data.has_priority_support is not None:
        plan.has_priority_support = plan_data.has_priority_support
    if plan_data.is_active is not None:
        plan.is_active = plan_data.is_active
    
    db.commit()
    db.refresh(plan)
    
    # Log plan update
    log = ActivityLog(
        user_id=current_user.id,
        salon_id=current_user.salon_id,
        action="updated",
        entity_type="plan",
        entity_id=plan.id,
        description=f"Updated plan {plan.name}",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    db.add(log)
    db.commit()
    
    return plan


@router.post("/{plan_id}/deactivate")
def deactivate_plan(
    plan_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superadmin)
):
    """Deactivate a plan (superadmin only)"""
    plan = db.query(Plan).filter(
        Plan.id == plan_id,
        Plan.deleted_at.is_(None)
    ).first()
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plan not found"
        )
    
    # Check if it's a free plan
    is_free = plan.monthly_price == 0 and plan.yearly_price == 0
    
    # Prevent deactivating free plan if it's the only active free plan
    if is_free:
        active_free_plans = db.query(func.count(Plan.id)).filter(
            Plan.monthly_price == 0,
            Plan.yearly_price == 0,
            Plan.is_active == 1,
            Plan.deleted_at.is_(None)
        ).scalar()
        
        if active_free_plans <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot deactivate the only active free plan"
            )
    
    plan.is_active = 0
    db.commit()
    
    # Log plan deactivation
    log = ActivityLog(
        user_id=current_user.id,
        salon_id=current_user.salon_id,
        action="deactivated",
        entity_type="plan",
        entity_id=plan.id,
        description=f"Deactivated plan {plan.name}",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    db.add(log)
    db.commit()
    
    return {"message": "Plan deactivated successfully"}


@router.post("/{plan_id}/activate")
def activate_plan(
    plan_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superadmin)
):
    """Activate a plan (superadmin only)"""
    plan = db.query(Plan).filter(
        Plan.id == plan_id,
        Plan.deleted_at.is_(None)
    ).first()
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plan not found"
        )
    
    plan.is_active = 1
    db.commit()
    
    # Log plan activation
    log = ActivityLog(
        user_id=current_user.id,
        salon_id=current_user.salon_id,
        action="activated",
        entity_type="plan",
        entity_id=plan.id,
        description=f"Activated plan {plan.name}",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    db.add(log)
    db.commit()
    
    return {"message": "Plan activated successfully"}


@router.delete("/{plan_id}")
def delete_plan(
    plan_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superadmin)
):
    """Soft delete a plan (superadmin only)"""
    plan = db.query(Plan).filter(
        Plan.id == plan_id,
        Plan.deleted_at.is_(None)
    ).first()
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plan not found"
        )
    
    # Check if it's a free plan
    is_free = plan.monthly_price == 0 and plan.yearly_price == 0
    
    # Prevent deleting free plan if it's the only one
    if is_free:
        active_free_plans = db.query(func.count(Plan.id)).filter(
            Plan.monthly_price == 0,
            Plan.yearly_price == 0,
            Plan.deleted_at.is_(None)
        ).scalar()
        
        if active_free_plans <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete the only free plan. At least one free plan must exist."
            )
    
    plan_name = plan.name
    # Soft delete
    plan.deleted_at = datetime.utcnow()
    plan.is_active = 0
    db.commit()
    
    # Log plan deletion
    log = ActivityLog(
        user_id=current_user.id,
        salon_id=current_user.salon_id,
        action="deleted",
        entity_type="plan",
        entity_id=plan_id,
        description=f"Deleted plan {plan_name}",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    db.add(log)
    db.commit()
    
    return {"message": "Plan deleted successfully"}
