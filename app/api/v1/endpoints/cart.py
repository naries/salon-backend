from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.models import Cart, CartItem, Product, Customer, User
from app.schemas.schemas import CartItemCreate, CartResponse
from app.core.security import get_current_admin_user, get_current_customer

router = APIRouter()

@router.get("/{customer_id}", response_model=CartResponse)
def get_customer_cart(
    customer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Get customer's cart."""
    customer = db.query(Customer).filter(
        Customer.id == customer_id,
        Customer.salon_id == current_user.salon_id
    ).first()
    
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    cart = db.query(Cart).filter(
        Cart.customer_id == customer_id,
        Cart.salon_id == current_user.salon_id
    ).first()
    
    if not cart:
        cart = Cart(customer_id=customer_id, salon_id=current_user.salon_id)
        db.add(cart)
        db.commit()
        db.refresh(cart)
    
    return cart


@router.post("/{customer_id}/items", response_model=CartResponse)
def add_item_to_cart(
    customer_id: int,
    item: CartItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Add item to cart."""
    customer = db.query(Customer).filter(
        Customer.id == customer_id,
        Customer.salon_id == current_user.salon_id
    ).first()
    
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    product = db.query(Product).filter(
        Product.id == item.product_id,
        Product.salon_id == current_user.salon_id,
        Product.is_active == 1,
        Product.deleted_at.is_(None)
    ).first()
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    if product.quantity < item.quantity:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient stock. Only {product.quantity} available"
        )
    
    cart = db.query(Cart).filter(
        Cart.customer_id == customer_id,
        Cart.salon_id == current_user.salon_id
    ).first()
    
    if not cart:
        cart = Cart(customer_id=customer_id, salon_id=current_user.salon_id)
        db.add(cart)
        db.commit()
        db.refresh(cart)
    
    cart_item = db.query(CartItem).filter(
        CartItem.cart_id == cart.id,
        CartItem.product_id == item.product_id
    ).first()
    
    if cart_item:
        new_qty = cart_item.quantity + item.quantity
        if product.quantity < new_qty:
            raise HTTPException(status_code=400, detail="Insufficient stock")
        cart_item.quantity = new_qty
    else:
        cart_item = CartItem(
            cart_id=cart.id,
            product_id=item.product_id,
            quantity=item.quantity
        )
        db.add(cart_item)
    
    db.commit()
    db.refresh(cart)
    return cart


@router.delete("/{customer_id}/items/{product_id}", response_model=CartResponse)
def remove_item_from_cart(
    customer_id: int,
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Remove item from cart."""
    cart = db.query(Cart).filter(
        Cart.customer_id == customer_id,
        Cart.salon_id == current_user.salon_id
    ).first()
    
    if not cart:
        raise HTTPException(status_code=404, detail="Cart not found")
    
    cart_item = db.query(CartItem).filter(
        CartItem.cart_id == cart.id,
        CartItem.product_id == product_id
    ).first()
    
    if not cart_item:
        raise HTTPException(status_code=404, detail="Item not in cart")
    
    db.delete(cart_item)
    db.commit()
    db.refresh(cart)
    return cart


# Customer endpoints (authenticated as customer)
@router.get("/my-cart", response_model=CartResponse)
def get_my_cart(
    db: Session = Depends(get_db),
    current_customer: Customer = Depends(get_current_customer)
):
    """Get current customer's cart."""
    cart = db.query(Cart).filter(
        Cart.customer_id == current_customer.id,
        Cart.salon_id == current_customer.salon_id
    ).first()
    
    if not cart:
        cart = Cart(customer_id=current_customer.id, salon_id=current_customer.salon_id)
        db.add(cart)
        db.commit()
        db.refresh(cart)
    
    return cart


@router.post("/my-cart/items", response_model=CartResponse)
def add_item_to_my_cart(
    item: CartItemCreate,
    db: Session = Depends(get_db),
    current_customer: Customer = Depends(get_current_customer)
):
    """Add item to current customer's cart."""
    # Check if product exists and belongs to the same salon
    product = db.query(Product).filter(
        Product.id == item.product_id,
        Product.salon_id == current_customer.salon_id,
        Product.is_active == 1
    ).first()
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Get or create cart
    cart = db.query(Cart).filter(
        Cart.customer_id == current_customer.id,
        Cart.salon_id == current_customer.salon_id
    ).first()
    
    if not cart:
        cart = Cart(customer_id=current_customer.id, salon_id=current_customer.salon_id)
        db.add(cart)
        db.commit()
        db.refresh(cart)
    
    # Check if item already in cart
    existing_item = db.query(CartItem).filter(
        CartItem.cart_id == cart.id,
        CartItem.product_id == item.product_id
    ).first()
    
    if existing_item:
        existing_item.quantity += item.quantity
    else:
        cart_item = CartItem(
            cart_id=cart.id,
            product_id=item.product_id,
            quantity=item.quantity
        )
        db.add(cart_item)
    
    db.commit()
    db.refresh(cart)
    return cart


@router.delete("/my-cart/items/{product_id}", response_model=CartResponse)
def remove_item_from_my_cart(
    product_id: int,
    db: Session = Depends(get_db),
    current_customer: Customer = Depends(get_current_customer)
):
    """Remove item from current customer's cart."""
    cart = db.query(Cart).filter(
        Cart.customer_id == current_customer.id,
        Cart.salon_id == current_customer.salon_id
    ).first()
    
    if not cart:
        raise HTTPException(status_code=404, detail="Cart not found")
    
    cart_item = db.query(CartItem).filter(
        CartItem.cart_id == cart.id,
        CartItem.product_id == product_id
    ).first()
    
    if not cart_item:
        raise HTTPException(status_code=404, detail="Item not in cart")
    
    db.delete(cart_item)
    db.commit()
    db.refresh(cart)
    return cart
