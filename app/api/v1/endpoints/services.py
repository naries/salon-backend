from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session, joinedload
from typing import List
from app.core.database import get_db
from app.core.security import get_current_admin_user
from app.models.models import Service, User, Salon, ActivityLog
from app.schemas.schemas import ServiceResponse, ServiceCreate, ServiceUpdate, ServiceWithSubServices

router = APIRouter()


@router.get("/by-salon/{salon_slug}/with-sub-services", response_model=List[ServiceWithSubServices])
def get_services_with_sub_services_by_salon_slug(
    salon_slug: str,
    db: Session = Depends(get_db)
):
    """Get all services with their sub-services for a salon by slug (public endpoint)"""
    salon = db.query(Salon).filter(Salon.slug == salon_slug, Salon.is_active == 1).first()
    if not salon:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Salon not found"
        )
    
    services = db.query(Service).options(
        joinedload(Service.sub_services)
    ).filter(Service.salon_id == salon.id).all()
    return services


@router.get("/by-salon/{salon_slug}", response_model=List[ServiceResponse])
def get_services_by_salon_slug(
    salon_slug: str,
    db: Session = Depends(get_db)
):
    """Get all services for a salon by slug (public endpoint for salon client)"""
    salon = db.query(Salon).filter(Salon.slug == salon_slug, Salon.is_active == 1).first()
    if not salon:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Salon not found"
        )
    
    services = db.query(Service).filter(Service.salon_id == salon.id).all()
    return services


@router.get("/", response_model=List[ServiceResponse])
def get_services(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Get all services for the admin's salon"""
    services = db.query(Service).filter(
        Service.salon_id == current_user.salon_id
    ).all()
    return services


@router.post("/", response_model=ServiceResponse, status_code=status.HTTP_201_CREATED)
def create_service(
    service_data: ServiceCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Create a new service (admin only) - can be from template or custom"""
    db_service = Service(
        salon_id=current_user.salon_id,
        service_template_id=service_data.service_template_id,
        name=service_data.name,
        description=service_data.description,
        price=service_data.price,
        duration_minutes=service_data.duration_minutes,
        is_custom=service_data.is_custom or 0
    )
    db.add(db_service)
    db.commit()
    db.refresh(db_service)
    
    # Log service creation
    log = ActivityLog(
        user_id=current_user.id,
        salon_id=current_user.salon_id,
        action="created",
        entity_type="service",
        entity_id=db_service.id,
        description=f"Created service {db_service.name}",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    db.add(log)
    db.commit()
    
    return db_service


@router.get("/{service_id}", response_model=ServiceResponse)
def get_service(
    service_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Get service by ID (admin only)"""
    service = db.query(Service).filter(
        Service.id == service_id,
        Service.salon_id == current_user.salon_id
    ).first()
    
    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service not found"
        )
    return service


@router.put("/{service_id}", response_model=ServiceResponse)
def update_service(
    service_id: int,
    service_data: ServiceUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Update a service (admin only) - salon can update price and duration"""
    service = db.query(Service).filter(
        Service.id == service_id,
        Service.salon_id == current_user.salon_id
    ).first()
    
    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service not found"
        )
    
    # Update fields if provided
    if service_data.name is not None:
        service.name = service_data.name
    if service_data.description is not None:
        service.description = service_data.description
    if service_data.price is not None:
        service.price = service_data.price
    if service_data.duration_minutes is not None:
        service.duration_minutes = service_data.duration_minutes
    service.duration_minutes = service_data.duration_minutes
    db.commit()
    db.refresh(service)
    
    # Log service update
    log = ActivityLog(
        user_id=current_user.id,
        salon_id=current_user.salon_id,
        action="updated",
        entity_type="service",
        entity_id=service.id,
        description=f"Updated service {service.name}",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    db.add(log)
    db.commit()
    
    return service


@router.delete("/{service_id}")
def delete_service(
    service_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Delete a service (admin only)"""
    service = db.query(Service).filter(
        Service.id == service_id,
        Service.salon_id == current_user.salon_id
    ).first()
    
    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service not found"
        )
    
    service_name = service.name
    db.delete(service)
    db.commit()
    
    # Log service deletion
    log = ActivityLog(
        user_id=current_user.id,
        salon_id=current_user.salon_id,
        action="deleted",
        entity_type="service",
        entity_id=service_id,
        description=f"Deleted service {service_name}",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    db.add(log)
    db.commit()
    
    return {"message": "Service deleted"}
