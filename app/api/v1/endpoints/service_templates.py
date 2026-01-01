from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.core.security import get_current_superadmin
from app.models.models import ServiceTemplate, User
from app.schemas.schemas import ServiceTemplateResponse, ServiceTemplateCreate, ServiceTemplateUpdate

router = APIRouter()


@router.get("/", response_model=List[ServiceTemplateResponse])
def get_service_templates(
    category: str = None,
    db: Session = Depends(get_db)
):
    """Get all active service templates (public endpoint for registration)"""
    query = db.query(ServiceTemplate).filter(ServiceTemplate.is_active == 1)
    
    if category:
        query = query.filter(ServiceTemplate.category == category)
    
    templates = query.all()
    return templates


@router.get("/{template_id}", response_model=ServiceTemplateResponse)
def get_service_template(template_id: int, db: Session = Depends(get_db)):
    """Get service template by ID"""
    template = db.query(ServiceTemplate).filter(ServiceTemplate.id == template_id).first()
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service template not found"
        )
    return template


@router.post("/", response_model=ServiceTemplateResponse, status_code=status.HTTP_201_CREATED)
def create_service_template(
    template_data: ServiceTemplateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superadmin)
):
    """Create a new service template (superadmin only)"""
    db_template = ServiceTemplate(
        name=template_data.name,
        description=template_data.description,
        category=template_data.category
    )
    db.add(db_template)
    db.commit()
    db.refresh(db_template)
    return db_template


@router.put("/{template_id}", response_model=ServiceTemplateResponse)
def update_service_template(
    template_id: int,
    template_data: ServiceTemplateUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superadmin)
):
    """Update service template (superadmin only) - can edit name, description, category"""
    template = db.query(ServiceTemplate).filter(ServiceTemplate.id == template_id).first()
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service template not found"
        )
    
    if template_data.name is not None:
        template.name = template_data.name
    if template_data.description is not None:
        template.description = template_data.description
    if template_data.category is not None:
        template.category = template_data.category
    if template_data.is_active is not None:
        template.is_active = template_data.is_active
    
    db.commit()
    db.refresh(template)
    return template


@router.delete("/{template_id}")
def delete_service_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superadmin)
):
    """Delete/deactivate service template (superadmin only)"""
    template = db.query(ServiceTemplate).filter(ServiceTemplate.id == template_id).first()
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service template not found"
        )
    
    # Soft delete
    template.is_active = 0
    db.commit()
    return {"message": "Service template deactivated"}
