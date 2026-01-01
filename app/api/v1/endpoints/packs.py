from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import User, Pack, PackProduct, Product
from app.schemas.pack import PackCreate, PackUpdate, PackResponse, PackListResponse, PackProductResponse
from datetime import datetime

router = APIRouter()


def calculate_pack_prices(pack: Pack, db: Session):
    """Calculate prices for a pack based on its products"""
    calculated_price = 0
    
    for pack_product in pack.pack_products:
        product = db.query(Product).filter(Product.id == pack_product.product_id).first()
        if product:
            # Use actual product price (without any discounts)
            calculated_price += product.price * pack_product.quantity
    
    # Determine effective price
    if pack.custom_price is not None:
        effective_price = pack.custom_price
    else:
        effective_price = calculated_price
    
    # Apply pack discount to effective price
    if pack.discount_percentage > 0:
        discount_amount = int(effective_price * (pack.discount_percentage / 100))
        effective_price -= discount_amount
    
    return calculated_price, effective_price


@router.post("/", response_model=PackResponse, status_code=status.HTTP_201_CREATED)
def create_pack(
    pack_data: PackCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new product pack (requires at least 2 products)"""
    if not current_user.salon_id:
        raise HTTPException(status_code=403, detail="Only salon admins can create packs")
    
    # Validate that all products exist and belong to the salon
    product_ids = [p.product_id for p in pack_data.products]
    products = db.query(Product).filter(
        Product.id.in_(product_ids),
        Product.salon_id == current_user.salon_id,
        Product.is_active == 1,
        Product.deleted_at.is_(None)
    ).all()
    
    if len(products) != len(product_ids):
        raise HTTPException(status_code=400, detail="One or more products not found or inactive")
    
    # Check for duplicate products
    if len(product_ids) != len(set(product_ids)):
        raise HTTPException(status_code=400, detail="Duplicate products not allowed in a pack")
    
    # Create pack
    new_pack = Pack(
        salon_id=current_user.salon_id,
        name=pack_data.name,
        description=pack_data.description,
        custom_price=pack_data.custom_price,
        discount_percentage=pack_data.discount_percentage
    )
    db.add(new_pack)
    db.flush()
    
    # Add products to pack
    for product_data in pack_data.products:
        pack_product = PackProduct(
            pack_id=new_pack.id,
            product_id=product_data.product_id,
            quantity=product_data.quantity
        )
        db.add(pack_product)
    
    db.commit()
    db.refresh(new_pack)
    
    # Calculate prices
    calculated_price, effective_price = calculate_pack_prices(new_pack, db)
    
    # Build response with product details
    products_response = []
    for pack_product in new_pack.pack_products:
        product = next(p for p in products if p.id == pack_product.product_id)
        products_response.append(PackProductResponse(
            id=pack_product.id,
            product_id=product.id,
            product_name=product.name,
            product_price=product.price,
            quantity=pack_product.quantity,
            total_price=product.price * pack_product.quantity
        ))
    
    return PackResponse(
        id=new_pack.id,
        salon_id=new_pack.salon_id,
        name=new_pack.name,
        description=new_pack.description,
        custom_price=new_pack.custom_price,
        discount_percentage=new_pack.discount_percentage,
        calculated_price=calculated_price,
        effective_price=effective_price,
        is_active=new_pack.is_active,
        products=products_response,
        created_at=new_pack.created_at,
        updated_at=new_pack.updated_at
    )


@router.get("/", response_model=List[PackListResponse])
def list_packs(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all packs for the current salon or all packs for superadmin"""
    # Superadmin sees all packs from all salons
    if current_user.is_superadmin == 1:
        packs = db.query(Pack).filter(
            Pack.deleted_at.is_(None)
        ).all()
    else:
        # Regular salon admin sees only their salon's packs
        if not current_user.salon_id:
            raise HTTPException(status_code=403, detail="Only salon admins can view packs")
        
        packs = db.query(Pack).filter(
            Pack.salon_id == current_user.salon_id,
            Pack.deleted_at.is_(None)
        ).all()
    
    result = []
    for pack in packs:
        calculated_price, effective_price = calculate_pack_prices(pack, db)
        product_count = len(pack.pack_products)
        
        result.append(PackListResponse(
            id=pack.id,
            salon_id=pack.salon_id,
            name=pack.name,
            description=pack.description,
            effective_price=effective_price,
            discount_percentage=pack.discount_percentage,
            product_count=product_count,
            is_active=pack.is_active,
            created_at=pack.created_at
        ))
    
    return result


@router.get("/{pack_id}", response_model=PackResponse)
def get_pack(
    pack_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific pack by ID"""
    pack = db.query(Pack).filter(
        Pack.id == pack_id,
        Pack.salon_id == current_user.salon_id,
        Pack.deleted_at.is_(None)
    ).first()
    
    if not pack:
        raise HTTPException(status_code=404, detail="Pack not found")
    
    calculated_price, effective_price = calculate_pack_prices(pack, db)
    
    # Build product details
    products_response = []
    for pack_product in pack.pack_products:
        product = db.query(Product).filter(Product.id == pack_product.product_id).first()
        if product:
            products_response.append(PackProductResponse(
                id=pack_product.id,
                product_id=product.id,
                product_name=product.name,
                product_price=product.price,
                quantity=pack_product.quantity,
                total_price=product.price * pack_product.quantity
            ))
    
    return PackResponse(
        id=pack.id,
        salon_id=pack.salon_id,
        name=pack.name,
        description=pack.description,
        custom_price=pack.custom_price,
        discount_percentage=pack.discount_percentage,
        calculated_price=calculated_price,
        effective_price=effective_price,
        is_active=pack.is_active,
        products=products_response,
        created_at=pack.created_at,
        updated_at=pack.updated_at
    )


@router.put("/{pack_id}", response_model=PackResponse)
def update_pack(
    pack_id: int,
    pack_data: PackUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a pack"""
    pack = db.query(Pack).filter(
        Pack.id == pack_id,
        Pack.salon_id == current_user.salon_id,
        Pack.deleted_at.is_(None)
    ).first()
    
    if not pack:
        raise HTTPException(status_code=404, detail="Pack not found")
    
    # Update basic fields
    if pack_data.name is not None:
        pack.name = pack_data.name
    if pack_data.description is not None:
        pack.description = pack_data.description
    if pack_data.custom_price is not None:
        pack.custom_price = pack_data.custom_price
    if pack_data.discount_percentage is not None:
        pack.discount_percentage = pack_data.discount_percentage
    if pack_data.is_active is not None:
        pack.is_active = pack_data.is_active
    
    # Update products if provided
    if pack_data.products is not None:
        # Validate products
        product_ids = [p.product_id for p in pack_data.products]
        products = db.query(Product).filter(
            Product.id.in_(product_ids),
            Product.salon_id == current_user.salon_id,
            Product.is_active == 1,
            Product.deleted_at.is_(None)
        ).all()
        
        if len(products) != len(product_ids):
            raise HTTPException(status_code=400, detail="One or more products not found or inactive")
        
        if len(product_ids) != len(set(product_ids)):
            raise HTTPException(status_code=400, detail="Duplicate products not allowed in a pack")
        
        # Remove old products
        db.query(PackProduct).filter(PackProduct.pack_id == pack.id).delete()
        
        # Add new products
        for product_data in pack_data.products:
            pack_product = PackProduct(
                pack_id=pack.id,
                product_id=product_data.product_id,
                quantity=product_data.quantity
            )
            db.add(pack_product)
    
    pack.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(pack)
    
    # Calculate prices
    calculated_price, effective_price = calculate_pack_prices(pack, db)
    
    # Build response
    products_response = []
    for pack_product in pack.pack_products:
        product = db.query(Product).filter(Product.id == pack_product.product_id).first()
        if product:
            products_response.append(PackProductResponse(
                id=pack_product.id,
                product_id=product.id,
                product_name=product.name,
                product_price=product.price,
                quantity=pack_product.quantity,
                total_price=product.price * pack_product.quantity
            ))
    
    return PackResponse(
        id=pack.id,
        salon_id=pack.salon_id,
        name=pack.name,
        description=pack.description,
        custom_price=pack.custom_price,
        discount_percentage=pack.discount_percentage,
        calculated_price=calculated_price,
        effective_price=effective_price,
        is_active=pack.is_active,
        products=products_response,
        created_at=pack.created_at,
        updated_at=pack.updated_at
    )


@router.delete("/{pack_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_pack(
    pack_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Soft delete a pack"""
    pack = db.query(Pack).filter(
        Pack.id == pack_id,
        Pack.salon_id == current_user.salon_id,
        Pack.deleted_at.is_(None)
    ).first()
    
    if not pack:
        raise HTTPException(status_code=404, detail="Pack not found")
    
    pack.deleted_at = datetime.utcnow()
    pack.is_active = 0
    db.commit()
    
    return None


@router.get("/public/by-salon/{salon_id}", response_model=List[PackResponse])
def get_public_packs(
    salon_id: int,
    db: Session = Depends(get_db)
):
    """Public endpoint to get all active packs for a salon"""
    packs = db.query(Pack).filter(
        Pack.salon_id == salon_id,
        Pack.is_active == 1,
        Pack.deleted_at.is_(None)
    ).all()
    
    result = []
    for pack in packs:
        calculated_price, effective_price = calculate_pack_prices(pack, db)
        
        # Build product details
        products_response = []
        for pack_product in pack.pack_products:
            product = db.query(Product).filter(
                Product.id == pack_product.product_id,
                Product.is_active == 1,
                Product.deleted_at.is_(None)
            ).first()
            if product:
                products_response.append(PackProductResponse(
                    id=pack_product.id,
                    product_id=product.id,
                    product_name=product.name,
                    product_price=product.price,
                    quantity=pack_product.quantity,
                    total_price=product.price * pack_product.quantity
                ))
        
        # Only include packs where all products are still active
        if len(products_response) >= 2:
            result.append(PackResponse(
                id=pack.id,
                salon_id=pack.salon_id,
                name=pack.name,
                description=pack.description,
                custom_price=pack.custom_price,
                discount_percentage=pack.discount_percentage,
                calculated_price=calculated_price,
                effective_price=effective_price,
                is_active=pack.is_active,
                products=products_response,
                created_at=pack.created_at,
                updated_at=pack.updated_at
            ))
    
    return result
