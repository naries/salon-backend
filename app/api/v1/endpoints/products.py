from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.database import get_db
from app.core.security import get_current_admin_user
from app.core.storage import validate_url
from app.models.models import Product, User, ActivityLog, CloudFile, ProductCategory, SubServiceProduct, SubService, ProductImage
from app.schemas.schemas import (
    ProductCreate, 
    ProductUpdate, 
    ProductResponse, 
    ProductImageResponse, 
    ProductImageUpdate,
    ProductImageUrlUpload,
    ProductImageUrlsUpload
)
from datetime import datetime

router = APIRouter()


def build_product_images(product, db):
    """Helper function to build product images list with URLs"""
    images = []
    for img in product.images:
        # Get the CloudFile to retrieve the URL
        cloud_file = db.query(CloudFile).filter(CloudFile.id == img.file_id).first() if img.file_id else None
        images.append({
            "id": img.id,
            "product_id": img.product_id,
            "file_id": img.file_id,
            "image_url": cloud_file.file_path if cloud_file else None,  # file_path now stores the full URL
            "display_order": img.display_order,
            "is_primary": img.is_primary,
            "created_at": img.created_at
        })
    return images


@router.get("/by-salon/{salon_id}")
def get_products_by_salon(
    salon_id: int,
    db: Session = Depends(get_db)
):
    """Public endpoint to get active products for a specific salon"""
    products = db.query(Product).filter(
        Product.salon_id == salon_id,
        Product.is_active == 1,
        Product.deleted_at == None
    ).order_by(Product.created_at.desc()).all()
    
    # Build response with image URLs and category names
    result = []
    for product in products:
        # Get the CloudFile to retrieve the URL
        image_url = None
        if product.image_file_id:
            cloud_file = db.query(CloudFile).filter(CloudFile.id == product.image_file_id).first()
            image_url = cloud_file.file_path if cloud_file else None
        
        product_dict = {
            "id": product.id,
            "salon_id": product.salon_id,
            "name": product.name,
            "description": product.description,
            "price": product.price,
            "discount_percentage": product.discount_percentage,
            "quantity": product.quantity,
            "category_id": product.category_id,
            "image_file_id": product.image_file_id,
            "is_active": product.is_active,
            "created_at": product.created_at,
            "updated_at": product.updated_at,
            "image_url": image_url,
            "category": None
        }
        
        # Add category name
        if product.category_id:
            category = db.query(ProductCategory).filter(ProductCategory.id == product.category_id).first()
            product_dict["category"] = category.name if category else None
        
        result.append(product_dict)
    
    return result
    
    return products


@router.get("/", response_model=List[ProductResponse])
def get_products(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
    include_inactive: bool = False
):
    """Get all products for the salon"""
    # Superadmin sees all products, regular admin sees only their salon's products
    if current_user.is_superadmin == 1:
        query = db.query(Product)
    else:
        query = db.query(Product).filter(Product.salon_id == current_user.salon_id)
    
    if not include_inactive:
        query = query.filter(Product.is_active == 1, Product.deleted_at == None)
    
    products = query.order_by(Product.created_at.desc()).all()
    
    # Build response with proper category names and image URLs
    result = []
    for product in products:
        # Get the CloudFile to retrieve the URL
        image_url = None
        if product.image_file_id:
            cloud_file = db.query(CloudFile).filter(CloudFile.id == product.image_file_id).first()
            image_url = cloud_file.file_path if cloud_file else None
        
        product_dict = {
            "id": product.id,
            "salon_id": product.salon_id,
            "name": product.name,
            "description": product.description,
            "price": product.price,
            "discount_percentage": product.discount_percentage,
            "quantity": product.quantity,
            "category_id": product.category_id,
            "image_file_id": product.image_file_id,
            "is_active": product.is_active,
            "created_at": product.created_at,
            "updated_at": product.updated_at,
            "image_url": image_url,
            "category": product.category.name if product.category else None,
            "images": build_product_images(product, db)
        }
        result.append(product_dict)
    
    return result


@router.post("/", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def create_product(
    product_data: ProductCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Create a new product"""
    # Determine salon_id: superadmin can specify, otherwise use their own
    if current_user.is_superadmin == 1 and product_data.salon_id:
        salon_id = product_data.salon_id
    else:
        salon_id = current_user.salon_id
    
    db_product = Product(
        salon_id=salon_id,
        name=product_data.name,
        description=product_data.description,
        price=product_data.price,
        discount_percentage=product_data.discount_percentage,
        quantity=product_data.quantity,
        category_id=product_data.category_id
    )
    
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    
    # Handle media IDs if provided
    if product_data.media_ids:
        from app.models.models import MediaUpload
        
        for idx, media_id in enumerate(product_data.media_ids):
            # Fetch MediaUpload record
            media_upload = db.query(MediaUpload).filter(
                MediaUpload.id == media_id,
                MediaUpload.status == "completed"
            ).first()
            
            if not media_upload:
                continue  # Skip if media not found or not completed
            
            # Create CloudFile record using media upload data
            cloud_file = CloudFile(
                filename=media_upload.original_filename,
                file_path=media_upload.public_url or media_upload.gcs_path,
                file_type=media_upload.file_type,
                file_size=media_upload.file_size,
                uploaded_by=current_user.id
            )
            db.add(cloud_file)
            db.flush()
            
            # Create ProductImage record
            product_image = ProductImage(
                product_id=db_product.id,
                file_id=cloud_file.id,
                is_primary=(idx == 0),  # First image is primary
                display_order=idx
            )
            db.add(product_image)
        
        db.commit()
        db.refresh(db_product)
    
    # Log activity
    log = ActivityLog(
        user_id=current_user.id,
        salon_id=salon_id,
        action="created",
        entity_type="product",
        entity_id=db_product.id,
        description=f"Created product: {db_product.name}",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    db.add(log)
    db.commit()
    
    db_product.image_url = None
    return db_product


@router.get("/{product_id}", response_model=ProductResponse)
def get_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Get a specific product"""
    query = db.query(Product).filter(Product.id == product_id)
    
    # Regular admin can only access their salon's products
    if current_user.is_superadmin != 1:
        query = query.filter(Product.salon_id == current_user.salon_id)
    
    product = query.first()
    
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    # Get the CloudFile to retrieve the URL
    if product.image_file_id:
        cloud_file = db.query(CloudFile).filter(CloudFile.id == product.image_file_id).first()
        product.image_url = cloud_file.file_path if cloud_file else None
    else:
        product.image_url = None
    
    return product


@router.put("/{product_id}", response_model=ProductResponse)
def update_product(
    product_id: int,
    product_data: ProductUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Update a product"""
    query = db.query(Product).filter(Product.id == product_id)
    
    # Regular admin can only update their salon's products
    if current_user.is_superadmin != 1:
        query = query.filter(Product.salon_id == current_user.salon_id)
    
    product = query.first()
    
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    if product_data.name is not None:
        product.name = product_data.name
    if product_data.description is not None:
        product.description = product_data.description
    if product_data.price is not None:
        product.price = product_data.price
    if product_data.discount_percentage is not None:
        product.discount_percentage = product_data.discount_percentage
    if product_data.quantity is not None:
        product.quantity = product_data.quantity
    if product_data.category_id is not None:
        product.category_id = product_data.category_id
    if product_data.is_active is not None:
        product.is_active = product_data.is_active
    
    db.commit()
    db.refresh(product)
    
    # Log activity
    log = ActivityLog(
        user_id=current_user.id,
        salon_id=current_user.salon_id,
        action="updated",
        entity_type="product",
        entity_id=product.id,
        description=f"Updated product: {product.name}",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    db.add(log)
    db.commit()
    
    # Get the CloudFile to retrieve the URL
    if product.image_file_id:
        cloud_file = db.query(CloudFile).filter(CloudFile.id == product.image_file_id).first()
        product.image_url = cloud_file.file_path if cloud_file else None
    else:
        product.image_url = None
    
    return product


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(
    product_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Soft delete a product"""
    product = db.query(Product).filter(
        Product.id == product_id,
        Product.salon_id == current_user.salon_id
    ).first()
    
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    # Soft delete
    product.is_active = 0
    product.deleted_at = datetime.utcnow()
    db.commit()
    
    # Log activity
    log = ActivityLog(
        user_id=current_user.id,
        salon_id=current_user.salon_id,
        action="deleted",
        entity_type="product",
        entity_id=product.id,
        description=f"Deleted product: {product.name}",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    db.add(log)
    db.commit()
    
    return None


@router.post("/{product_id}/upload-image")
def upload_product_image_url(
    product_id: int,
    image_data: ProductImageUrlUpload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Save product image URL
    
    Frontend should upload image directly to GCS and send the public URL here.
    """
    product = db.query(Product).filter(
        Product.id == product_id,
        Product.salon_id == current_user.salon_id
    ).first()
    
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    # Validate URL format
    if not validate_url(image_data.image_url):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid image URL"
        )
    
    # Create CloudFile entry
    cloud_file = CloudFile(
        filename=image_data.filename or "product_image.png",
        file_path=image_data.image_url,  # Store the full URL as file_path
        file_type="image/png",  # Default to PNG
        file_size=image_data.file_size or 0,
        uploaded_by=current_user.id
    )
    db.add(cloud_file)
    db.commit()
    db.refresh(cloud_file)
    
    # Update product
    product.image_file_id = cloud_file.id
    db.commit()
    
    return {
        "success": True,
        "message": "Image URL saved successfully",
        "file_id": cloud_file.id,
        "file_url": image_data.image_url
    }


# === MULTIPLE IMAGES ENDPOINTS ===

@router.get("/{product_id}/images")
def get_product_images(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Get all images for a product"""
    product = db.query(Product).filter(Product.id == product_id).first()
    
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    # Check access
    if current_user.is_superadmin != 1 and product.salon_id != current_user.salon_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    return build_product_images(product, db)


@router.post("/{product_id}/images")
def upload_product_images_urls(
    product_id: int,
    images_data: ProductImageUrlsUpload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Save multiple product images from media IDs or URLs
    
    Preferred: Upload files to /media/upload first, then pass media_ids here.
    Legacy: Pass image_urls directly.
    """
    product = db.query(Product).filter(
        Product.id == product_id,
        Product.salon_id == current_user.salon_id
    ).first()
    
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    # Get current max display order
    max_order = db.query(ProductImage).filter(
        ProductImage.product_id == product_id
    ).count()
    
    uploaded_images = []
    
    # Handle media_ids (new preferred method)
    if images_data.media_ids:
        from app.models.models import MediaUpload
        
        for idx, media_id in enumerate(images_data.media_ids):
            # Fetch MediaUpload record
            media_upload = db.query(MediaUpload).filter(
                MediaUpload.id == media_id,
                MediaUpload.status == "completed"
            ).first()
            
            if not media_upload:
                continue  # Skip if media not found or not completed
            
            # Create CloudFile record using media upload data
            cloud_file = CloudFile(
                filename=media_upload.original_filename,
                file_path=media_upload.public_url or media_upload.gcs_path,
                file_type=media_upload.file_type,
                file_size=media_upload.file_size,
                uploaded_by=current_user.id
            )
            db.add(cloud_file)
            db.flush()
            
            # Check if this is the first image (make it primary)
            is_first = max_order == 0 and idx == 0
            
            # Create ProductImage entry
            product_image = ProductImage(
                product_id=product_id,
                file_id=cloud_file.id,
                display_order=max_order + idx,
                is_primary=1 if is_first else 0
            )
            db.add(product_image)
            uploaded_images.append(product_image)
        
        db.commit()
    
    # Handle image_urls (legacy method)
    elif images_data.image_urls:
        for idx, image_url in enumerate(images_data.image_urls):
            # Validate URL format
            if not validate_url(image_url):
                continue  # Skip invalid URLs
            
            # Get filename if provided
            filename = "product_image.png"
            if images_data.filenames and idx < len(images_data.filenames):
                filename = images_data.filenames[idx]
            
            # Create CloudFile entry
            cloud_file = CloudFile(
                filename=filename,
                file_path=image_url,
                file_type="image/png",
                file_size=0,
                uploaded_by=current_user.id
            )
            db.add(cloud_file)
            db.flush()
            
            # Check if this is the first image (make it primary)
            is_first = max_order == 0 and idx == 0
            
            # Create ProductImage entry
            product_image = ProductImage(
                product_id=product_id,
                file_id=cloud_file.id,
                display_order=max_order + idx,
                is_primary=1 if is_first else 0
            )
            db.add(product_image)
            uploaded_images.append(product_image)
        
        db.commit()
    
    # Set first image as main product image if applicable
    if uploaded_images and (max_order == 0):
        product.image_file_id = uploaded_images[0].file_id
        db.commit()
    
    # Refresh all uploaded images
    for img in uploaded_images:
        db.refresh(img)
    
    return {
        "success": True,
        "message": f"Saved {len(uploaded_images)} images",
        "images": [
            {
                "id": img.id,
                "product_id": img.product_id,
                "file_id": img.file_id,
                "display_order": img.display_order,
                "is_primary": img.is_primary
            }
            for img in uploaded_images
        ]
    }


@router.put("/{product_id}/images/{image_id}")
def update_product_image(
    product_id: int,
    image_id: int,
    image_data: ProductImageUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Update a product image (set as primary or change order)"""
    product = db.query(Product).filter(
        Product.id == product_id,
        Product.salon_id == current_user.salon_id
    ).first()
    
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    image = db.query(ProductImage).filter(
        ProductImage.id == image_id,
        ProductImage.product_id == product_id
    ).first()
    
    if not image:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found"
        )
    
    if image_data.is_primary is not None and image_data.is_primary == 1:
        # Unset current primary
        db.query(ProductImage).filter(
            ProductImage.product_id == product_id,
            ProductImage.is_primary == 1
        ).update({"is_primary": 0})
        image.is_primary = 1
        # Also update main product image
        product.image_file_id = image.file_id
    
    if image_data.display_order is not None:
        image.display_order = image_data.display_order
    
    db.commit()
    db.refresh(image)
    
    return {
        "id": image.id,
        "product_id": image.product_id,
        "file_id": image.file_id,
        "image_url": f"http://localhost:8000/api/v1/files/{image.file_id}" if image.file_id else None,
        "display_order": image.display_order,
        "is_primary": image.is_primary,
        "created_at": image.created_at
    }


@router.delete("/{product_id}/images/{image_id}")
def delete_product_image(
    product_id: int,
    image_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Delete a product image"""
    product = db.query(Product).filter(
        Product.id == product_id,
        Product.salon_id == current_user.salon_id
    ).first()
    
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    image = db.query(ProductImage).filter(
        ProductImage.id == image_id,
        ProductImage.product_id == product_id
    ).first()
    
    if not image:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found"
        )
    
    was_primary = image.is_primary == 1
    file_id = image.file_id
    
    db.delete(image)
    db.commit()
    
    # If this was the primary image, set another as primary
    if was_primary:
        next_image = db.query(ProductImage).filter(
            ProductImage.product_id == product_id
        ).order_by(ProductImage.display_order).first()
        
        if next_image:
            next_image.is_primary = 1
            product.image_file_id = next_image.file_id
        else:
            product.image_file_id = None
        
        db.commit()
    
    return {"success": True, "message": "Image deleted"}


@router.put("/{product_id}/images/reorder")
def reorder_product_images(
    product_id: int,
    image_ids: List[int],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Reorder product images"""
    product = db.query(Product).filter(
        Product.id == product_id,
        Product.salon_id == current_user.salon_id
    ).first()
    
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    for idx, image_id in enumerate(image_ids):
        db.query(ProductImage).filter(
            ProductImage.id == image_id,
            ProductImage.product_id == product_id
        ).update({"display_order": idx})
    
    db.commit()
    
    return {"success": True, "message": "Images reordered"}


@router.get("/suggested/{sub_service_id}")
def get_suggested_products(
    sub_service_id: int,
    db: Session = Depends(get_db)
):
    """Public endpoint to get suggested products for a sub-service"""
    # Get sub-service to verify it exists and get salon_id
    sub_service = db.query(SubService).filter(SubService.id == sub_service_id).first()
    if not sub_service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sub-service not found"
        )
    
    # Get suggested products for this sub-service
    suggested_products = db.query(Product).join(
        SubServiceProduct, Product.id == SubServiceProduct.product_id
    ).filter(
        SubServiceProduct.sub_service_id == sub_service_id,
        Product.is_active == 1,
        Product.deleted_at == None
    ).order_by(Product.name).all()
    
    # Build response with image URLs and category names
    result = []
    for product in suggested_products:
        product_dict = {
            "id": product.id,
            "salon_id": product.salon_id,
            "name": product.name,
            "description": product.description,
            "price": product.price,
            "discount_percentage": product.discount_percentage,
            "quantity": product.quantity,
            "category_id": product.category_id,
            "image_file_id": product.image_file_id,
            "is_active": product.is_active,
            "created_at": product.created_at,
            "updated_at": product.updated_at,
            "image_url": f"http://localhost:8000/api/v1/files/{product.image_file_id}" if product.image_file_id else None,
            "category": None,
            "final_price": product.price - (product.price * product.discount_percentage / 100) if product.discount_percentage > 0 else product.price
        }
        
        # Add category name
        if product.category_id:
            category = db.query(ProductCategory).filter(ProductCategory.id == product.category_id).first()
            product_dict["category"] = category.name if category else None
        
        result.append(product_dict)
    
    return result
