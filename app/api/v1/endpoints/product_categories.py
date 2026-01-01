from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from app.core.database import get_db
from app.core.security import get_current_admin_user
from app.models.models import ProductCategory, User, ActivityLog, Salon
from app.schemas.schemas import ProductCategoryCreate, ProductCategoryUpdate, ProductCategoryResponse

router = APIRouter()


@router.get("/", response_model=List[ProductCategoryResponse])
def get_product_categories(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """Get all product categories for the salon"""
    if current_user.is_superadmin == 1:
        # Superadmin sees all categories from all salons
        categories = db.query(ProductCategory).order_by(ProductCategory.created_at.desc()).all()
    else:
        # Salon admin sees only their salon's categories
        categories = db.query(ProductCategory).filter(
            ProductCategory.salon_id == current_user.salon_id
        ).order_by(ProductCategory.created_at.desc()).all()
    
    return categories


@router.post("/", response_model=ProductCategoryResponse, status_code=status.HTTP_201_CREATED)
def create_product_category(
    category_data: ProductCategoryCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Create a new product category"""
    # Determine salon_id: superadmin can specify, otherwise use their own
    if current_user.is_superadmin == 1 and category_data.salon_id:
        salon_id = category_data.salon_id
    else:
        salon_id = current_user.salon_id
    
    # Check for duplicate category name in the same salon
    existing = db.query(ProductCategory).filter(
        ProductCategory.salon_id == salon_id,
        ProductCategory.name == category_data.name
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A category with this name already exists for this salon"
        )
    
    db_category = ProductCategory(
        salon_id=salon_id,
        name=category_data.name,
        description=category_data.description
    )
    
    db.add(db_category)
    db.commit()
    db.refresh(db_category)
    
    # Log activity
    log = ActivityLog(
        user_id=current_user.id,
        salon_id=salon_id,
        action="created",
        entity_type="product_category",
        entity_id=db_category.id,
        description=f"Created product category: {db_category.name}",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    db.add(log)
    db.commit()
    
    return db_category


@router.get("/{category_id}", response_model=ProductCategoryResponse)
def get_product_category(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Get a specific product category"""
    category = db.query(ProductCategory).filter(ProductCategory.id == category_id).first()
    
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product category not found"
        )
    
    # Check permissions
    if current_user.is_superadmin != 1 and category.salon_id != current_user.salon_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    return category


@router.put("/{category_id}", response_model=ProductCategoryResponse)
def update_product_category(
    category_id: int,
    category_data: ProductCategoryUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Update a product category"""
    category = db.query(ProductCategory).filter(ProductCategory.id == category_id).first()
    
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product category not found"
        )
    
    # Check permissions
    if current_user.is_superadmin != 1 and category.salon_id != current_user.salon_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Check for duplicate name if name is being updated
    if category_data.name and category_data.name != category.name:
        existing = db.query(ProductCategory).filter(
            ProductCategory.salon_id == category.salon_id,
            ProductCategory.name == category_data.name,
            ProductCategory.id != category_id
        ).first()
        
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A category with this name already exists for this salon"
            )
    
    if category_data.name is not None:
        category.name = category_data.name
    if category_data.description is not None:
        category.description = category_data.description
    
    db.commit()
    db.refresh(category)
    
    # Log activity
    log = ActivityLog(
        user_id=current_user.id,
        salon_id=category.salon_id,
        action="updated",
        entity_type="product_category",
        entity_id=category.id,
        description=f"Updated product category: {category.name}",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    db.add(log)
    db.commit()
    
    return category


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product_category(
    category_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Delete a product category"""
    category = db.query(ProductCategory).filter(ProductCategory.id == category_id).first()
    
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product category not found"
        )
    
    # Check permissions
    if current_user.is_superadmin != 1 and category.salon_id != current_user.salon_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Log activity before deletion
    log = ActivityLog(
        user_id=current_user.id,
        salon_id=category.salon_id,
        action="deleted",
        entity_type="product_category",
        entity_id=category.id,
        description=f"Deleted product category: {category.name}",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    db.add(log)
    
    # Delete the category (products will have category_id set to NULL due to ondelete="SET NULL")
    db.delete(category)
    db.commit()
    
    return None


# Superadmin specific endpoints
@router.get("/superadmin/all")
def get_all_categories_with_salon_info(
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Get all product categories across all salons (superadmin only)"""
    if current_user.is_superadmin != 1:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Superadmin access required"
        )
    
    # Base query with salon info
    query = db.query(ProductCategory).options(joinedload(ProductCategory.salon))
    
    # Apply search filter
    if search:
        query = query.join(Salon).filter(
            (ProductCategory.name.ilike(f"%{search}%")) |
            (Salon.name.ilike(f"%{search}%"))
        )
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    categories = query.order_by(ProductCategory.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()
    
    # Format response
    result = {
        "categories": [],
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page
    }
    
    for category in categories:
        result["categories"].append({
            "id": category.id,
            "salon_id": category.salon_id,
            "salon_name": category.salon.name if category.salon else None,
            "name": category.name,
            "description": category.description,
            "created_at": category.created_at,
            "updated_at": category.updated_at
        })
    
    return result
