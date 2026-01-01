from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from random import shuffle
from app.core.database import get_db
from app.models.models import Product, Salon, ProductCategory, Review, Pack, PackProduct
from pydantic import BaseModel
from datetime import datetime

router = APIRouter()


class ShowroomProductResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    price: int
    discount_percentage: float = 0
    final_price: int
    quantity: int
    category: Optional[str] = None
    image_url: Optional[str] = None
    salon_id: int
    salon_name: str
    salon_slug: str
    salon_logo_type: str
    salon_logo_icon_name: str
    salon_logo_file_id: Optional[int] = None
    salon_rating: float = 0.0
    salon_review_count: int = 0

    class Config:
        from_attributes = True


class ShowroomResponse(BaseModel):
    products: List[ShowroomProductResponse]
    total_count: int
    page: int
    per_page: int
    total_pages: int
    categories: List[str]


class ShowroomPackProductResponse(BaseModel):
    id: int
    name: str
    price: int
    quantity: int
    image_url: Optional[str] = None

    class Config:
        from_attributes = True


class ShowroomPackResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    custom_price: Optional[int] = None
    calculated_price: int
    final_price: int
    discount_percentage: float = 0
    product_count: int
    products: List[ShowroomPackProductResponse]
    salon_id: int
    salon_name: str
    salon_slug: str
    salon_logo_type: str
    salon_logo_icon_name: str
    salon_logo_file_id: Optional[int] = None
    salon_rating: float = 0.0
    salon_review_count: int = 0

    class Config:
        from_attributes = True


class CategoryCount(BaseModel):
    name: str
    count: int


def get_salon_rating(db: Session, salon_id: int) -> tuple:
    """Get average rating and review count for a salon"""
    reviews = db.query(Review).filter(
        Review.salon_id == salon_id,
        Review.is_approved == 1,
        Review.is_visible == 1
    ).all()
    
    total_reviews = len(reviews)
    average_rating = round(sum(r.rating for r in reviews) / total_reviews, 1) if total_reviews > 0 else 0.0
    
    return average_rating, total_reviews


@router.get("/", response_model=ShowroomResponse)
def get_showroom_products(
    page: int = Query(1, ge=1),
    per_page: int = Query(24, ge=1, le=100),
    category: Optional[str] = Query(None, description="Filter by category name"),
    min_price: Optional[int] = Query(None, description="Minimum price in kobo"),
    max_price: Optional[int] = Query(None, description="Maximum price in kobo"),
    sort_by: Optional[str] = Query("random", description="Sort by: random, price_low, price_high, newest, rating"),
    search: Optional[str] = Query(None, description="Search products by name"),
    db: Session = Depends(get_db)
):
    """
    Get randomized products from all active salons for the showroom.
    Public endpoint - no authentication required.
    """
    # Base query for active products from active salons
    query = db.query(Product).join(Salon).filter(
        Product.is_active == 1,
        Product.deleted_at == None,
        Product.quantity > 0,
        Salon.is_active == 1
    )
    
    # Apply filters
    if category:
        query = query.join(ProductCategory, Product.category_id == ProductCategory.id).filter(
            func.lower(ProductCategory.name) == category.lower()
        )
    
    if min_price is not None:
        query = query.filter(Product.price >= min_price)
    
    if max_price is not None:
        query = query.filter(Product.price <= max_price)
    
    if search:
        search_term = f"%{search.lower()}%"
        query = query.filter(func.lower(Product.name).like(search_term))
    
    # Get total count before pagination
    total_count = query.count()
    
    # Get all products for sorting (needed for random shuffle)
    all_products = query.all()
    
    # Sort products
    if sort_by == "price_low":
        all_products = sorted(all_products, key=lambda p: p.price - (p.price * p.discount_percentage / 100))
    elif sort_by == "price_high":
        all_products = sorted(all_products, key=lambda p: p.price - (p.price * p.discount_percentage / 100), reverse=True)
    elif sort_by == "newest":
        all_products = sorted(all_products, key=lambda p: p.created_at, reverse=True)
    elif sort_by == "rating":
        # Pre-fetch ratings for salons
        salon_ratings = {}
        for product in all_products:
            if product.salon_id not in salon_ratings:
                salon_ratings[product.salon_id] = get_salon_rating(db, product.salon_id)
        all_products = sorted(all_products, key=lambda p: salon_ratings.get(p.salon_id, (0, 0))[0], reverse=True)
    else:  # random
        shuffle(all_products)
    
    # Apply pagination
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    paginated_products = all_products[start_idx:end_idx]
    
    # Get all unique categories for filters
    all_categories = db.query(ProductCategory.name).distinct().filter(
        ProductCategory.id.in_(
            db.query(Product.category_id).filter(
                Product.is_active == 1,
                Product.deleted_at == None,
                Product.quantity > 0,
                Product.category_id.isnot(None)
            ).distinct()
        )
    ).all()
    categories = [c[0] for c in all_categories if c[0]]
    
    # Build response
    result_products = []
    for product in paginated_products:
        salon = product.salon
        rating, review_count = get_salon_rating(db, salon.id)
        
        final_price = product.price
        if product.discount_percentage > 0:
            final_price = int(product.price - (product.price * product.discount_percentage / 100))
        
        product_data = ShowroomProductResponse(
            id=product.id,
            name=product.name,
            description=product.description,
            price=product.price,
            discount_percentage=product.discount_percentage,
            final_price=final_price,
            quantity=product.quantity,
            category=product.category.name if product.category else None,
            image_url=f"http://localhost:8000/api/v1/files/{product.image_file_id}" if product.image_file_id else None,
            salon_id=salon.id,
            salon_name=salon.name,
            salon_slug=salon.slug,
            salon_logo_type=salon.logo_type,
            salon_logo_icon_name=salon.logo_icon_name,
            salon_logo_file_id=salon.logo_file_id,
            salon_rating=rating,
            salon_review_count=review_count
        )
        result_products.append(product_data)
    
    total_pages = (total_count + per_page - 1) // per_page
    
    return ShowroomResponse(
        products=result_products,
        total_count=total_count,
        page=page,
        per_page=per_page,
        total_pages=total_pages,
        categories=sorted(categories)
    )


@router.get("/featured")
def get_featured_products(
    limit: int = Query(8, ge=1, le=24),
    db: Session = Depends(get_db)
):
    """
    Get featured products for homepage showcase.
    Returns products from top-rated salons with discounts prioritized.
    """
    # Get products with discounts first, then others
    products_query = db.query(Product).join(Salon).filter(
        Product.is_active == 1,
        Product.deleted_at == None,
        Product.quantity > 0,
        Salon.is_active == 1
    ).order_by(Product.discount_percentage.desc(), func.random()).limit(limit * 2).all()
    
    # Shuffle and limit
    shuffle(products_query)
    featured = products_query[:limit]
    
    result = []
    for product in featured:
        salon = product.salon
        rating, review_count = get_salon_rating(db, salon.id)
        
        final_price = product.price
        if product.discount_percentage > 0:
            final_price = int(product.price - (product.price * product.discount_percentage / 100))
        
        result.append({
            "id": product.id,
            "name": product.name,
            "description": product.description,
            "price": product.price,
            "discount_percentage": product.discount_percentage,
            "final_price": final_price,
            "quantity": product.quantity,
            "category": product.category.name if product.category else None,
            "image_url": f"http://localhost:8000/api/v1/files/{product.image_file_id}" if product.image_file_id else None,
            "salon_id": salon.id,
            "salon_name": salon.name,
            "salon_slug": salon.slug,
            "salon_logo_type": salon.logo_type,
            "salon_logo_icon_name": salon.logo_icon_name,
            "salon_logo_file_id": salon.logo_file_id,
            "salon_rating": rating,
            "salon_review_count": review_count
        })
    
    return result


@router.get("/categories")
def get_product_categories(db: Session = Depends(get_db)):
    """
    Get all product categories with product counts.
    """
    # Get categories with product counts
    categories = db.query(
        ProductCategory.name,
        func.count(Product.id).label('count')
    ).join(
        Product, ProductCategory.id == Product.category_id
    ).join(
        Salon, Product.salon_id == Salon.id
    ).filter(
        Product.is_active == 1,
        Product.deleted_at == None,
        Product.quantity > 0,
        Salon.is_active == 1
    ).group_by(ProductCategory.name).all()
    
    return [{"name": c[0], "count": c[1]} for c in categories]


@router.get("/product/{product_id}")
def get_product_details(
    product_id: int,
    db: Session = Depends(get_db)
):
    """
    Get detailed information about a specific product.
    """
    product = db.query(Product).join(Salon).filter(
        Product.id == product_id,
        Product.is_active == 1,
        Product.deleted_at == None,
        Salon.is_active == 1
    ).first()
    
    if not product:
        return {"error": "Product not found"}
    
    salon = product.salon
    rating, review_count = get_salon_rating(db, salon.id)
    
    final_price = product.price
    if product.discount_percentage > 0:
        final_price = int(product.price - (product.price * product.discount_percentage / 100))
    
    # Get all product images
    product_images = []
    # Add main image first if exists
    if product.image_file_id:
        product_images.append({
            "id": product.image_file_id,
            "url": f"http://localhost:8000/api/v1/files/{product.image_file_id}",
            "is_primary": True
        })
    # Add additional images from ProductImage table
    for img in product.images:
        if img.file_id and img.file_id != product.image_file_id:
            product_images.append({
                "id": img.file_id,
                "url": f"http://localhost:8000/api/v1/files/{img.file_id}",
                "is_primary": img.is_primary == 1
            })
    
    # Get related products from same salon
    related_products = db.query(Product).filter(
        Product.salon_id == salon.id,
        Product.id != product_id,
        Product.is_active == 1,
        Product.deleted_at == None,
        Product.quantity > 0
    ).limit(4).all()
    
    related = []
    for rp in related_products:
        rp_final = rp.price
        if rp.discount_percentage > 0:
            rp_final = int(rp.price - (rp.price * rp.discount_percentage / 100))
        related.append({
            "id": rp.id,
            "name": rp.name,
            "price": rp.price,
            "discount_percentage": rp.discount_percentage,
            "final_price": rp_final,
            "image_url": f"http://localhost:8000/api/v1/files/{rp.image_file_id}" if rp.image_file_id else None
        })
    
    return {
        "id": product.id,
        "name": product.name,
        "description": product.description,
        "price": product.price,
        "discount_percentage": product.discount_percentage,
        "final_price": final_price,
        "quantity": product.quantity,
        "category": product.category.name if product.category else None,
        "image_url": f"http://localhost:8000/api/v1/files/{product.image_file_id}" if product.image_file_id else None,
        "images": product_images,
        "salon": {
            "id": salon.id,
            "name": salon.name,
            "slug": salon.slug,
            "address": salon.address,
            "phone": salon.phone,
            "logo_type": salon.logo_type,
            "logo_icon_name": salon.logo_icon_name,
            "logo_file_id": salon.logo_file_id,
            "rating": rating,
            "review_count": review_count
        },
        "related_products": related
    }


@router.get("/packs")
def get_showroom_packs(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    sort_by: Optional[str] = Query("random", description="Sort by: random, price_low, price_high, newest"),
    search: Optional[str] = Query(None, description="Search packs by name"),
    db: Session = Depends(get_db)
):
    """
    Get packs from all active salons for the showroom.
    """
    # Base query for active packs from active salons
    query = db.query(Pack).join(Salon).filter(
        Pack.is_active == 1,
        Pack.deleted_at == None,
        Salon.is_active == 1
    )
    
    if search:
        search_term = f"%{search.lower()}%"
        query = query.filter(func.lower(Pack.name).like(search_term))
    
    # Get total count
    total_count = query.count()
    
    all_packs = query.all()
    
    # Calculate prices for sorting
    def get_pack_price(pack):
        if pack.custom_price:
            price = pack.custom_price
        else:
            price = sum(pp.product.price * pp.quantity for pp in pack.pack_products if pp.product)
        if pack.discount_percentage > 0:
            price = int(price - (price * pack.discount_percentage / 100))
        return price
    
    # Sort packs
    if sort_by == "price_low":
        all_packs = sorted(all_packs, key=get_pack_price)
    elif sort_by == "price_high":
        all_packs = sorted(all_packs, key=get_pack_price, reverse=True)
    elif sort_by == "newest":
        all_packs = sorted(all_packs, key=lambda p: p.created_at, reverse=True)
    else:  # random
        shuffle(all_packs)
    
    # Apply pagination
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    paginated_packs = all_packs[start_idx:end_idx]
    
    # Build response
    result_packs = []
    for pack in paginated_packs:
        salon = pack.salon
        rating, review_count = get_salon_rating(db, salon.id)
        
        # Calculate pack price
        calculated_price = sum(pp.product.price * pp.quantity for pp in pack.pack_products if pp.product)
        base_price = pack.custom_price if pack.custom_price else calculated_price
        final_price = base_price
        if pack.discount_percentage > 0:
            final_price = int(base_price - (base_price * pack.discount_percentage / 100))
        
        # Get products in pack
        pack_products = []
        for pp in pack.pack_products:
            if pp.product:
                pack_products.append({
                    "id": pp.product.id,
                    "name": pp.product.name,
                    "price": pp.product.price,
                    "quantity": pp.quantity,
                    "image_url": f"http://localhost:8000/api/v1/files/{pp.product.image_file_id}" if pp.product.image_file_id else None
                })
        
        result_packs.append({
            "id": pack.id,
            "name": pack.name,
            "description": pack.description,
            "custom_price": pack.custom_price,
            "calculated_price": calculated_price,
            "final_price": final_price,
            "discount_percentage": pack.discount_percentage,
            "product_count": len(pack.pack_products),
            "products": pack_products,
            "salon_id": salon.id,
            "salon_name": salon.name,
            "salon_slug": salon.slug,
            "salon_logo_type": salon.logo_type,
            "salon_logo_icon_name": salon.logo_icon_name,
            "salon_logo_file_id": salon.logo_file_id,
            "salon_rating": rating,
            "salon_review_count": review_count
        })
    
    total_pages = (total_count + per_page - 1) // per_page
    
    return {
        "packs": result_packs,
        "total_count": total_count,
        "page": page,
        "per_page": per_page,
        "total_pages": total_pages
    }


class PlatformStatsResponse(BaseModel):
    total_salons: int
    total_products: int
    total_packs: int
    total_bookings: int
    average_rating: float
    featured_products: List[ShowroomProductResponse]


@router.get("/platform-stats")
def get_platform_stats(db: Session = Depends(get_db)):
    """Get platform-wide stats for landing page"""
    from app.models.models import Appointment
    
    # Count active salons (with at least one product or service)
    total_salons = db.query(Salon).filter(Salon.is_active == 1).count()
    
    # Count products in stock
    total_products = db.query(Product).filter(Product.quantity > 0).count()
    
    # Count active packs
    total_packs = db.query(Pack).filter(Pack.is_active == 1).count()
    
    # Count completed bookings
    total_bookings = db.query(Appointment).filter(
        Appointment.status.in_(["completed", "confirmed"])
    ).count()
    
    # Calculate average rating across all salons
    avg_rating_result = db.query(func.avg(Review.rating)).scalar()
    average_rating = round(float(avg_rating_result), 1) if avg_rating_result else 4.5
    
    # Get 4 random featured products (prefer ones with images but fallback to any)
    featured_query = db.query(Product, Salon).join(
        Salon, Product.salon_id == Salon.id
    ).filter(
        Product.quantity > 0,
        Salon.is_active == 1
    ).order_by(
        # Prefer products with images
        Product.image_file_id.desc().nulls_last()
    ).limit(20).all()
    
    # Shuffle and take 4
    featured_list = list(featured_query)
    shuffle(featured_list)
    featured_list = featured_list[:4]
    
    featured_products = []
    for product, salon in featured_list:
        # Get salon rating
        rating_result = db.query(func.avg(Review.rating)).filter(Review.salon_id == salon.id).scalar()
        rating = round(float(rating_result), 1) if rating_result else 0.0
        review_count = db.query(Review).filter(Review.salon_id == salon.id).count()
        
        final_price = product.price
        if product.discount_percentage:
            final_price = int(product.price * (1 - product.discount_percentage / 100))
        
        featured_products.append({
            "id": product.id,
            "name": product.name,
            "description": product.description,
            "price": product.price,
            "discount_percentage": product.discount_percentage or 0,
            "final_price": final_price,
            "quantity": product.quantity,
            "category": product.category.name if product.category else None,
            "image_url": f"http://localhost:8000/api/v1/files/{product.image_file_id}" if product.image_file_id else None,
            "salon_id": salon.id,
            "salon_name": salon.name,
            "salon_slug": salon.slug,
            "salon_logo_type": salon.logo_type,
            "salon_logo_icon_name": salon.logo_icon_name,
            "salon_logo_file_id": salon.logo_file_id,
            "salon_rating": rating,
            "salon_review_count": review_count
        })
    
    return {
        "total_salons": total_salons,
        "total_products": total_products,
        "total_packs": total_packs,
        "total_bookings": total_bookings,
        "average_rating": average_rating,
        "featured_products": featured_products
    }
