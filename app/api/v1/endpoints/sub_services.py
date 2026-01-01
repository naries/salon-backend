from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.core.security import get_current_admin_user
from app.models.models import SubService, Service, User, SubServiceProduct, Product, ProductCategory
from app.schemas.schemas import (
    SubServiceResponse, 
    SubServiceCreate, 
    SubServiceUpdate,
    SubServiceProductResponse,
    SubServiceWithProducts
)

router = APIRouter()


@router.get("/by-service/{service_id}", response_model=List[SubServiceResponse])
def get_sub_services_by_service(
    service_id: int,
    db: Session = Depends(get_db)
):
    """Get all active sub-services for a specific service (public endpoint)"""
    # Verify service exists
    service = db.query(Service).filter(Service.id == service_id).first()
    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service not found"
        )
    
    sub_services = db.query(SubService).filter(
        SubService.service_id == service_id,
        SubService.is_active == 1
    ).all()
    return sub_services


@router.get("/", response_model=List[SubServiceResponse])
def get_sub_services(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Get all sub-services for the admin's salon"""
    # Get all services for this salon
    services = db.query(Service).filter(
        Service.salon_id == current_user.salon_id
    ).all()
    
    service_ids = [s.id for s in services]
    
    sub_services = db.query(SubService).filter(
        SubService.service_id.in_(service_ids)
    ).all()
    return sub_services


@router.post("/", response_model=SubServiceResponse, status_code=status.HTTP_201_CREATED)
def create_sub_service(
    sub_service_data: SubServiceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Create a new sub-service (admin only)"""
    # Verify service exists and belongs to admin's salon
    service = db.query(Service).filter(
        Service.id == sub_service_data.service_id,
        Service.salon_id == current_user.salon_id
    ).first()
    
    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service not found or does not belong to your salon"
        )
    
    # Create sub-service
    db_sub_service = SubService(
        service_id=sub_service_data.service_id,
        name=sub_service_data.name,
        description=sub_service_data.description,
        pricing_type=sub_service_data.pricing_type if sub_service_data.pricing_type else "hourly",
        hourly_rate=sub_service_data.hourly_rate,
        min_hours=sub_service_data.min_hours if sub_service_data.pricing_type == "hourly" else None,
        is_active=1
    )
    db.add(db_sub_service)
    db.commit()
    db.refresh(db_sub_service)
    return db_sub_service


@router.get("/{sub_service_id}", response_model=SubServiceResponse)
def get_sub_service(
    sub_service_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Get sub-service by ID (admin only, must belong to their salon)"""
    sub_service = db.query(SubService).join(Service).filter(
        SubService.id == sub_service_id,
        Service.salon_id == current_user.salon_id
    ).first()
    
    if not sub_service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sub-service not found"
        )
    return sub_service


@router.put("/{sub_service_id}", response_model=SubServiceResponse)
def update_sub_service(
    sub_service_id: int,
    sub_service_data: SubServiceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Update a sub-service (admin only)"""
    sub_service = db.query(SubService).join(Service).filter(
        SubService.id == sub_service_id,
        Service.salon_id == current_user.salon_id
    ).first()
    
    if not sub_service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sub-service not found"
        )
    
    # Update fields if provided
    if sub_service_data.name is not None:
        sub_service.name = sub_service_data.name
    if sub_service_data.description is not None:
        sub_service.description = sub_service_data.description
    if sub_service_data.hourly_rate is not None:
        sub_service.hourly_rate = sub_service_data.hourly_rate
    if sub_service_data.is_active is not None:
        sub_service.is_active = sub_service_data.is_active
    
    db.commit()
    db.refresh(sub_service)
    return sub_service


@router.delete("/{sub_service_id}")
def delete_sub_service(
    sub_service_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Delete a sub-service (admin only)"""
    sub_service = db.query(SubService).join(Service).filter(
        SubService.id == sub_service_id,
        Service.salon_id == current_user.salon_id
    ).first()
    
    if not sub_service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sub-service not found"
        )
    
    db.delete(sub_service)
    db.commit()
    return {"message": "Sub-service deleted"}


# Sub-service product management endpoints
@router.post("/{sub_service_id}/products/{product_id}", response_model=SubServiceProductResponse, status_code=status.HTTP_201_CREATED)
def add_product_to_sub_service(
    sub_service_id: int,
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Add a product to sub-service suggestions (admin only)"""
    # Verify sub-service exists and belongs to admin's salon
    sub_service = db.query(SubService).join(Service).filter(
        SubService.id == sub_service_id,
        Service.salon_id == current_user.salon_id
    ).first()
    
    if not sub_service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sub-service not found"
        )
    
    # Verify product exists and belongs to admin's salon
    product = db.query(Product).filter(
        Product.id == product_id,
        Product.salon_id == current_user.salon_id
    ).first()
    
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found or does not belong to your salon"
        )
    
    # Check if association already exists
    existing = db.query(SubServiceProduct).filter(
        SubServiceProduct.sub_service_id == sub_service_id,
        SubServiceProduct.product_id == product_id
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Product already added to this sub-service"
        )
    
    # Create association
    association = SubServiceProduct(
        sub_service_id=sub_service_id,
        product_id=product_id
    )
    db.add(association)
    db.commit()
    db.refresh(association)
    
    # Get category name if exists
    category_name = None
    if product.category_id:
        category = db.query(ProductCategory).filter(ProductCategory.id == product.category_id).first()
        if category:
            category_name = category.name
    
    # Return response with product details
    return {
        'id': association.id,
        'sub_service_id': association.sub_service_id,
        'product_id': association.product_id,
        'created_at': association.created_at,
        'product': {
            'id': product.id,
            'name': product.name,
            'description': product.description,
            'price': product.price,
            'discount_percentage': product.discount_percentage,
            'quantity': product.quantity,
            'category_id': product.category_id,
            'salon_id': product.salon_id,
            'image_file_id': product.image_file_id,
            'category': category_name,
            'is_active': product.is_active,
            'created_at': product.created_at,
            'updated_at': product.updated_at
        }
    }


@router.delete("/{sub_service_id}/products/{product_id}")
def remove_product_from_sub_service(
    sub_service_id: int,
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Remove a product from sub-service suggestions (admin only)"""
    # Verify sub-service exists and belongs to admin's salon
    sub_service = db.query(SubService).join(Service).filter(
        SubService.id == sub_service_id,
        Service.salon_id == current_user.salon_id
    ).first()
    
    if not sub_service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sub-service not found"
        )
    
    # Find and delete association
    association = db.query(SubServiceProduct).filter(
        SubServiceProduct.sub_service_id == sub_service_id,
        SubServiceProduct.product_id == product_id
    ).first()
    
    if not association:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not associated with this sub-service"
        )
    
    db.delete(association)
    db.commit()
    return {"message": "Product removed from sub-service suggestions"}


@router.get("/{sub_service_id}/products", response_model=List[SubServiceProductResponse])
def get_sub_service_products(
    sub_service_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Get all suggested products for a sub-service (admin only)"""
    # Verify sub-service exists and belongs to admin's salon
    sub_service = db.query(SubService).join(Service).filter(
        SubService.id == sub_service_id,
        Service.salon_id == current_user.salon_id
    ).first()
    
    if not sub_service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sub-service not found"
        )
    
    # Get all product associations for this sub-service with product details
    associations = db.query(SubServiceProduct).filter(
        SubServiceProduct.sub_service_id == sub_service_id
    ).all()
    
    # Manually load product details for each association to avoid relationship issues
    result = []
    for assoc in associations:
        product = db.query(Product).filter(Product.id == assoc.product_id).first()
        if product:
            # Get category name if exists
            category_name = None
            if product.category_id:
                category = db.query(ProductCategory).filter(ProductCategory.id == product.category_id).first()
                if category:
                    category_name = category.name
            
            # Create response dict
            assoc_dict = {
                'id': assoc.id,
                'sub_service_id': assoc.sub_service_id,
                'product_id': assoc.product_id,
                'created_at': assoc.created_at,
                'product': {
                    'id': product.id,
                    'name': product.name,
                    'description': product.description,
                    'price': product.price,
                    'discount_percentage': product.discount_percentage,
                    'quantity': product.quantity,
                    'category_id': product.category_id,
                    'salon_id': product.salon_id,
                    'image_file_id': product.image_file_id,
                    'category': category_name,
                    'is_active': product.is_active,
                    'created_at': product.created_at,
                    'updated_at': product.updated_at
                }
            }
            result.append(assoc_dict)
    
    return result


@router.get("/{sub_service_id}/with-products", response_model=SubServiceWithProducts)
def get_sub_service_with_products(
    sub_service_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Get sub-service with its suggested products (admin only)"""
    # Verify sub-service exists and belongs to admin's salon
    sub_service = db.query(SubService).join(Service).filter(
        SubService.id == sub_service_id,
        Service.salon_id == current_user.salon_id
    ).first()
    
    if not sub_service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sub-service not found"
        )
    
    return sub_service


@router.get("/{sub_service_id}/products/public", response_model=List[SubServiceProductResponse])
def get_sub_service_products_public(
    sub_service_id: int,
    db: Session = Depends(get_db)
):
    """Get all suggested products for a sub-service (public endpoint for customers)"""
    # Verify sub-service exists and is active
    sub_service = db.query(SubService).filter(
        SubService.id == sub_service_id,
        SubService.is_active == 1
    ).first()
    
    if not sub_service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sub-service not found"
        )
    
    # Get all active product associations for this sub-service
    associations = db.query(SubServiceProduct).join(Product).filter(
        SubServiceProduct.sub_service_id == sub_service_id,
        Product.is_active == 1
    ).all()
    
    return associations
