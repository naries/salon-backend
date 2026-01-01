from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import List
import re
from app.core.database import get_db
from app.core.security import get_current_superadmin, get_current_admin_user, get_password_hash
from app.models.models import Salon, User, Service, ServiceTemplate, Plan, ActivityLog
from app.schemas.schemas import SalonResponse, SalonRegistration, SalonHoursUpdate, SalonUpdate

router = APIRouter()


def generate_slug(name: str, db: Session) -> str:
    """Generate a unique slug from salon name"""
    # Convert to lowercase and replace spaces/special chars with hyphens
    base_slug = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')
    
    # Ensure uniqueness
    slug = base_slug
    counter = 1
    while db.query(Salon).filter(Salon.slug == slug).first():
        slug = f"{base_slug}-{counter}"
        counter += 1
    
    return slug


@router.post("/register", response_model=SalonResponse, status_code=status.HTTP_201_CREATED)
def register_salon(
    registration_data: SalonRegistration,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Complete salon registration with multi-step data:
    1. Salon info
    2. Admin user
    3. Selected services
    4. Plan selection
    """
    # Check if salon email already exists
    existing_salon = db.query(Salon).filter(Salon.email == registration_data.email).first()
    if existing_salon:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Salon with this email already exists"
        )
    
    # Check if admin email already exists
    existing_user = db.query(User).filter(User.email == registration_data.admin_email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists"
        )
    
    # Verify plan exists
    plan = db.query(Plan).filter(Plan.id == registration_data.plan_id).first()
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Selected plan not found"
        )
    
    # Generate unique slug for salon
    slug = generate_slug(registration_data.name, db)
    
    # Create salon
    db_salon = Salon(
        name=registration_data.name,
        slug=slug,
        address=registration_data.address,
        phone=registration_data.phone,
        email=registration_data.email,
        plan_id=registration_data.plan_id,
        billing_cycle=registration_data.billing_cycle,
        auto_debit=registration_data.auto_debit,
        is_active=1
    )
    db.add(db_salon)
    db.flush()
    
    # Create admin user for salon
    db_user = User(
        email=registration_data.admin_email,
        full_name=registration_data.admin_full_name,
        hashed_password=get_password_hash(registration_data.admin_password),
        salon_id=db_salon.id,
        is_admin=1,
        is_superadmin=0
    )
    db.add(db_user)
    db.flush()
    
    # Create services from templates (salon will set price and duration later)
    for template_id in registration_data.selected_service_template_ids:
        template = db.query(ServiceTemplate).filter(ServiceTemplate.id == template_id).first()
        if template:
            service = Service(
                salon_id=db_salon.id,
                service_template_id=template.id,
                name=template.name,
                description=template.description,
                is_custom=0  # Template-based service
            )
            db.add(service)
    
    db.commit()
    db.refresh(db_salon)
    
    # Log salon registration
    log = ActivityLog(
        user_id=db_user.id,
        salon_id=db_salon.id,
        action="created",
        entity_type="salon",
        entity_id=db_salon.id,
        description=f"Registered new salon {db_salon.name} with {len(registration_data.selected_service_template_ids)} services",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    db.add(log)
    db.commit()
    
    return db_salon


@router.get("/my-salon", response_model=SalonResponse)
def get_my_salon(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Get current user's salon (for regular admins)"""
    if not current_user.salon_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No salon associated with this user"
        )
    
    salon = db.query(Salon).filter(Salon.id == current_user.salon_id).first()
    if not salon:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Salon not found"
        )
    return salon


@router.put("/my-salon", response_model=SalonResponse)
def update_my_salon(
    salon_update: SalonUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Update salon settings (admin only)"""
    if not current_user.salon_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No salon associated with this user"
        )
    
    salon = db.query(Salon).filter(Salon.id == current_user.salon_id).first()
    if not salon:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Salon not found"
        )
    
    # Update fields if provided
    update_data = salon_update.dict(exclude_unset=True)
    
    # Validate hours if provided
    if 'opening_hour' in update_data or 'closing_hour' in update_data:
        opening = update_data.get('opening_hour', salon.opening_hour)
        closing = update_data.get('closing_hour', salon.closing_hour)
        
        if opening < 0 or opening > 23:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Opening hour must be between 0 and 23"
            )
        
        if closing < 0 or closing > 23:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Closing hour must be between 0 and 23"
            )
        
        if opening >= closing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Opening hour must be before closing hour"
            )
    
    # Validate max concurrent slots if provided
    if 'max_concurrent_slots' in update_data:
        if update_data['max_concurrent_slots'] < 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Max concurrent slots must be at least 1"
            )
    
    # Validate billing cycle if provided
    if 'billing_cycle' in update_data:
        if update_data['billing_cycle'] not in ['monthly', 'yearly']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Billing cycle must be 'monthly' or 'yearly'"
            )
    
    # Validate auto_debit if provided
    if 'auto_debit' in update_data:
        if update_data['auto_debit'] not in [0, 1]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Auto debit must be 0 or 1"
            )
    
    # Apply updates
    for field, value in update_data.items():
        setattr(salon, field, value)
    
    db.commit()
    db.refresh(salon)
    
    # Log salon update
    log = ActivityLog(
        user_id=current_user.id,
        salon_id=current_user.salon_id,
        action="updated",
        entity_type="salon",
        entity_id=salon.id,
        description=f"Updated salon settings for {salon.name}",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    db.add(log)
    db.commit()
    
    return salon


@router.get("/by-slug/{slug}", response_model=SalonResponse)
def get_salon_by_slug(
    slug: str,
    db: Session = Depends(get_db)
):
    """Get salon by slug (public endpoint for salon client access)"""
    salon = db.query(Salon).filter(Salon.slug == slug, Salon.is_active == 1).first()
    if not salon:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Salon not found"
        )
    return salon


@router.get("/", response_model=List[SalonResponse])
def get_all_salons(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superadmin)
):
    """Get all salons (superadmin only)"""
    salons = db.query(Salon).all()
    return salons


@router.get("/{salon_id}", response_model=SalonResponse)
def get_salon(
    salon_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superadmin)
):
    """Get salon by ID (superadmin only)"""
    salon = db.query(Salon).filter(Salon.id == salon_id).first()
    if not salon:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Salon not found"
        )
    return salon


@router.put("/{salon_id}/activate", response_model=SalonResponse)
def activate_salon(
    salon_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superadmin)
):
    """Activate/deactivate salon (superadmin only)"""
    salon = db.query(Salon).filter(Salon.id == salon_id).first()
    if not salon:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Salon not found"
        )
    
    old_status = salon.is_active
    salon.is_active = 1 if salon.is_active == 0 else 0
    db.commit()
    db.refresh(salon)
    
    # Log salon activation/deactivation
    action_text = "activated" if salon.is_active == 1 else "deactivated"
    log = ActivityLog(
        user_id=current_user.id,
        salon_id=current_user.salon_id,
        action=action_text,
        entity_type="salon",
        entity_id=salon.id,
        description=f"{action_text.capitalize()} salon {salon.name}",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    db.add(log)
    db.commit()
    
    return salon


@router.put("/my-salon/hours", response_model=SalonResponse)
def update_salon_hours(
    hours_update: SalonHoursUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Update salon operating hours and max concurrent slots (admin only)"""
    if not current_user.salon_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No salon associated with this user"
        )
    
    salon = db.query(Salon).filter(Salon.id == current_user.salon_id).first()
    if not salon:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Salon not found"
        )
    
    # Validate hours
    if hours_update.opening_hour < 0 or hours_update.opening_hour > 23:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Opening hour must be between 0 and 23"
        )
    
    if hours_update.closing_hour < 0 or hours_update.closing_hour > 23:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Closing hour must be between 0 and 23"
        )
    
    if hours_update.opening_hour >= hours_update.closing_hour:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Opening hour must be before closing hour"
        )
    
    # Update hours
    salon.opening_hour = hours_update.opening_hour
    salon.closing_hour = hours_update.closing_hour
    
    if hours_update.max_concurrent_slots is not None:
        if hours_update.max_concurrent_slots < 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Max concurrent slots must be at least 1"
            )
        salon.max_concurrent_slots = hours_update.max_concurrent_slots
    
    db.commit()
    db.refresh(salon)
    return salon
