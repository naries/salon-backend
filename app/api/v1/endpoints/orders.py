from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import List, Optional
import secrets
import requests
import json
from datetime import datetime
from app.core.database import get_db
from app.models.models import Order, OrderItem, Cart, CartItem, Product, Customer, User, ActivityLog, Pack, PackProduct, Wallet, WalletTransaction, SalonCustomer, Salon
from app.schemas.schemas import OrderResponse, PaymentInitiate
from app.core.security import get_current_admin_user, get_current_customer_optional
from app.api.v1.endpoints.customer_auth import get_or_create_salon_customer
from app.services.notification_service import NotificationService

router = APIRouter()

# Payment gateway configurations (should be in environment variables)
PAYSTACK_SECRET_KEY = "sk_test_..."  # Replace with actual key from env
FLUTTERWAVE_SECRET_KEY = "FLWSECK_TEST..."  # Replace with actual key from env


def generate_order_number() -> str:
    """Generate unique order number."""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    random_suffix = secrets.token_hex(4).upper()
    return f"ORD-{timestamp}-{random_suffix}"


@router.post("/initiate/{customer_id}", response_model=dict)
def initiate_order(
    customer_id: int,
    payment_data: PaymentInitiate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Initiate order and payment (salon admin only)."""
    # Verify customer belongs to salon
    customer = db.query(Customer).filter(
        Customer.id == customer_id,
        Customer.salon_id == current_user.salon_id
    ).first()
    
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found"
        )
    
    # Get cart
    cart = db.query(Cart).filter(
        Cart.customer_id == customer_id,
        Cart.salon_id == current_user.salon_id
    ).first()
    
    if not cart or not cart.items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cart is empty"
        )
    
    # Calculate total and verify stock
    total_amount = 0
    for cart_item in cart.items:
        product = cart_item.product
        
        # Verify product still active
        if not product.is_active or product.deleted_at:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Product '{product.name}' is no longer available"
            )
        
        # Verify stock
        if product.quantity < cart_item.quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient stock for '{product.name}'. Only {product.quantity} available"
            )
        
        total_amount += product.price * cart_item.quantity
    
    # Create order
    order_number = generate_order_number()
    order = Order(
        order_number=order_number,
        customer_id=customer_id,
        salon_id=current_user.salon_id,
        total_amount=total_amount,
        status="pending",
        payment_method=payment_data.payment_method
    )
    db.add(order)
    db.flush()
    
    # Create order items
    for cart_item in cart.items:
        order_item = OrderItem(
            order_id=order.id,
            product_id=cart_item.product_id,
            quantity=cart_item.quantity,
            price_at_purchase=cart_item.product.price
        )
        db.add(order_item)
    
    db.commit()
    db.refresh(order)
    
    # Initialize payment with gateway
    payment_response = {}
    
    if payment_data.payment_method == "paystack":
        # Initialize Paystack payment
        paystack_url = "https://api.paystack.co/transaction/initialize"
        headers = {
            "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "email": customer.email,
            "amount": total_amount,  # Paystack expects amount in kobo (cents)
            "reference": order_number,
            "callback_url": payment_data.callback_url or "https://yourdomain.com/payment/verify",
            "metadata": {
                "order_id": order.id,
                "customer_id": customer.id,
                "salon_id": customer.salon_id
            }
        }
        
        try:
            response = requests.post(paystack_url, json=payload, headers=headers)
            response.raise_for_status()
            paystack_data = response.json()
            
            if paystack_data["status"]:
                payment_response = {
                    "authorization_url": paystack_data["data"]["authorization_url"],
                    "access_code": paystack_data["data"]["access_code"],
                    "reference": paystack_data["data"]["reference"]
                }
                
                # Update order with payment reference
                order.payment_reference = paystack_data["data"]["reference"]
                order.payment_data = paystack_data["data"]
                db.commit()
        except requests.exceptions.RequestException as e:
            db.delete(order)
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Payment initialization failed: {str(e)}"
            )
    
    elif payment_data.payment_method == "flutterwave":
        # Initialize Flutterwave payment
        flutterwave_url = "https://api.flutterwave.com/v3/payments"
        headers = {
            "Authorization": f"Bearer {FLUTTERWAVE_SECRET_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "tx_ref": order_number,
            "amount": total_amount / 100,  # Flutterwave expects amount in naira
            "currency": "NGN",
            "redirect_url": payment_data.callback_url or "https://yourdomain.com/payment/verify",
            "customer": {
                "email": customer.email,
                "name": customer.name,
                "phonenumber": customer.phone or ""
            },
            "customizations": {
                "title": "Product Purchase",
                "description": f"Order {order_number}"
            },
            "meta": {
                "order_id": order.id,
                "customer_id": customer.id,
                "salon_id": customer.salon_id
            }
        }
        
        try:
            response = requests.post(flutterwave_url, json=payload, headers=headers)
            response.raise_for_status()
            flutterwave_data = response.json()
            
            if flutterwave_data["status"] == "success":
                payment_response = {
                    "authorization_url": flutterwave_data["data"]["link"],
                    "reference": order_number
                }
                
                # Update order
                order.payment_reference = order_number
                order.payment_data = flutterwave_data["data"]
                db.commit()
        except requests.exceptions.RequestException as e:
            db.delete(order)
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Payment initialization failed: {str(e)}"
            )
    else:
        db.delete(order)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid payment method"
        )
    
    # Log activity
    log = ActivityLog(
        user_id=current_user.id,
        salon_id=current_user.salon_id,
        action="order_initiated",
        entity_type="order",
        entity_id=order.id,
        details=f"Order {order_number} initiated for customer {customer.name} with {payment_data.payment_method}"
    )
    db.add(log)
    db.commit()
    
    return {
        "order_id": order.id,
        "order_number": order_number,
        "total_amount": total_amount,
        "payment_method": payment_data.payment_method,
        **payment_response
    }


@router.post("/verify/{reference}")
def verify_payment(
    reference: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Verify payment and complete order (salon admin only)."""
    # Find order
    order = db.query(Order).filter(
        Order.payment_reference == reference,
        Order.salon_id == current_user.salon_id
    ).first()
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    if order.status == "paid":
        return {"status": "success", "message": "Payment already verified", "order": order}
    
    # Verify with payment gateway
    verification_successful = False
    
    if order.payment_method == "paystack":
        # Verify with Paystack
        verify_url = f"https://api.paystack.co/transaction/verify/{reference}"
        headers = {"Authorization": f"Bearer {PAYSTACK_SECRET_KEY}"}
        
        try:
            response = requests.get(verify_url, headers=headers)
            response.raise_for_status()
            paystack_data = response.json()
            
            if paystack_data["status"] and paystack_data["data"]["status"] == "success":
                verification_successful = True
                order.payment_data = paystack_data["data"]
        except requests.exceptions.RequestException as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Payment verification failed: {str(e)}"
            )
    
    elif order.payment_method == "flutterwave":
        # Verify with Flutterwave
        verify_url = f"https://api.flutterwave.com/v3/transactions/{reference}/verify"
        headers = {"Authorization": f"Bearer {FLUTTERWAVE_SECRET_KEY}"}
        
        try:
            response = requests.get(verify_url, headers=headers)
            response.raise_for_status()
            flutterwave_data = response.json()
            
            if flutterwave_data["status"] == "success" and flutterwave_data["data"]["status"] == "successful":
                verification_successful = True
                order.payment_data = flutterwave_data["data"]
        except requests.exceptions.RequestException as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Payment verification failed: {str(e)}"
            )
    
    if verification_successful:
        # Update order status
        order.status = "paid"
        
        # Reduce product quantities
        for order_item in order.items:
            product = order_item.product
            if product.quantity >= order_item.quantity:
                product.quantity -= order_item.quantity
            else:
                # This shouldn't happen if we validated correctly, but handle it
                order.status = "failed"
                db.commit()
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Insufficient stock for product '{product.name}'"
                )
        
        # Get or create wallet for salon
        wallet = db.query(Wallet).filter(Wallet.salon_id == order.salon_id).first()
        if not wallet:
            wallet = Wallet(salon_id=order.salon_id, balance=0)
            db.add(wallet)
            db.flush()
        
        # Create wallet transaction
        wallet_transaction = WalletTransaction(
            wallet_id=wallet.id,
            order_id=order.id,
            amount=order.total_amount,
            type="credit",
            status="completed",
            payment_reference=reference,
            description=f"Payment for order {order.order_number}",
            transaction_data=json.dumps({"payment_method": order.payment_method})
        )
        db.add(wallet_transaction)
        
        # Update wallet balance
        wallet.balance += order.total_amount
        
        # Clear customer's cart
        cart = db.query(Cart).filter(
            Cart.customer_id == order.customer_id,
            Cart.salon_id == current_user.salon_id
        ).first()
        
        if cart:
            db.query(CartItem).filter(CartItem.cart_id == cart.id).delete()
        
        db.commit()
        
        # Log activity
        log = ActivityLog(
            user_id=current_user.id,
            salon_id=current_user.salon_id,
            action="order_completed",
            entity_type="order",
            entity_id=order.id,
            details=f"Order {order.order_number} completed successfully"
        )
        db.add(log)
        
        # Send notification to salon about order
        try:
            salon = db.query(Salon).filter(Salon.id == order.salon_id).first()
            if salon:
                items_summary = ", ".join([
                    f"{item.quantity}x {item.product.name}" for item in order.items if item.product
                ])
                notification_service = NotificationService(db)
                notification_service.notify_order_placed(
                    order=order,
                    salon=salon,
                    items_summary=items_summary
                )
        except Exception as e:
            print(f"[NOTIFICATION ERROR] Failed to send order notification: {e}")
        
        return {
            "status": "success",
            "message": "Payment verified successfully",
            "order": order
        }
    else:
        order.status = "failed"
        db.commit()
        return {
            "status": "failed",
            "message": "Payment verification failed"
        }


@router.get("/", response_model=List[OrderResponse])
def get_orders(
    status: str = None,
    search: str = None,
    start_date: str = None,
    end_date: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Get all orders for salon with filters (salon admin only)."""
    query = db.query(Order).filter(Order.salon_id == current_user.salon_id)
    
    # Apply filters
    if status:
        query = query.filter(Order.status == status)
    
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (Order.order_number.ilike(search_term)) |
            (Order.customer_name.ilike(search_term)) |
            (Order.customer_email.ilike(search_term)) |
            (Order.customer_phone.ilike(search_term))
        )
    
    if start_date:
        try:
            start = datetime.fromisoformat(start_date)
            query = query.filter(Order.created_at >= start)
        except ValueError:
            pass
    
    if end_date:
        try:
            end = datetime.fromisoformat(end_date)
            query = query.filter(Order.created_at <= end)
        except ValueError:
            pass
    
    orders = query.order_by(Order.created_at.desc()).all()
    return orders


@router.get("/{order_id}", response_model=OrderResponse)
def get_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Get specific order details (salon admin only)."""
    order = db.query(Order).filter(
        Order.id == order_id,
        Order.salon_id == current_user.salon_id
    ).first()
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    return order


@router.post("/public/create", response_model=dict)
def create_public_order(
    order_data: dict,
    request: Request,
    db: Session = Depends(get_db),
    current_customer: Optional[Customer] = Depends(get_current_customer_optional)
):
    """
    Create order from web client. 
    
    Supports both:
    - Guest checkout (no authentication)
    - Authenticated customer checkout (creates SalonCustomer relationship)
    
    Supports both products and packs.
    """
    # Extract data
    salon_id = order_data.get("salon_id")
    customer_name = order_data.get("customer_name")
    customer_email = order_data.get("customer_email")
    customer_phone = order_data.get("customer_phone")
    items = order_data.get("items", [])
    
    if not all([salon_id, customer_name, customer_email, customer_phone, items]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing required fields"
        )
    
    # Validate items and calculate total
    total_amount = 0
    order_items = []
    
    for item in items:
        is_pack = item.get("is_pack", False)
        
        if is_pack:
            # Handle pack
            pack_id = item.get("pack_id")
            if not pack_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Pack ID required for pack items"
                )
            
            pack = db.query(Pack).filter(
                Pack.id == pack_id,
                Pack.salon_id == salon_id,
                Pack.is_active == 1,
                Pack.deleted_at.is_(None)
            ).first()
            
            if not pack:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Pack with id {pack_id} not found or inactive"
                )
            
            # Calculate pack price
            if pack.custom_price is not None:
                pack_price = pack.custom_price
            else:
                # Calculate from products
                pack_price = sum(
                    pp.product.price * pp.quantity 
                    for pp in pack.pack_products 
                    if pp.product.is_active and not pp.product.deleted_at
                )
            
            # Apply pack discount
            if pack.discount_percentage > 0:
                pack_price = pack_price * (1 - pack.discount_percentage / 100)
            
            # Verify stock for all products in pack
            for pack_product in pack.pack_products:
                product = pack_product.product
                required_quantity = pack_product.quantity * item["quantity"]
                
                if not product.is_active or product.deleted_at:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Product '{product.name}' in pack is no longer available"
                    )
                
                if product.quantity < required_quantity:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Insufficient stock for '{product.name}' in pack. Need {required_quantity}, only {product.quantity} available"
                    )
            
            total_amount += pack_price * item["quantity"]
            order_items.append({
                "type": "pack",
                "pack": pack,
                "quantity": item["quantity"],
                "price": pack_price
            })
        else:
            # Handle regular product
            product_id = item.get("product_id")
            if not product_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Product ID required for product items"
                )
            
            product = db.query(Product).filter(
                Product.id == product_id,
                Product.salon_id == salon_id
            ).first()
            
            if not product:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Product with id {product_id} not found"
                )
            
            if not product.is_active or product.deleted_at:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Product '{product.name}' is no longer available"
                )
            
            if product.quantity < item["quantity"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Insufficient stock for '{product.name}'. Only {product.quantity} available"
                )
            
            # Calculate price (product discounts don't apply in packs, but apply to individual purchases)
            price = product.price
            if product.discount_percentage and product.discount_percentage > 0:
                price = price * (1 - product.discount_percentage / 100)
            
            total_amount += price * item["quantity"]
            order_items.append({
                "type": "product",
                "product": product,
                "quantity": item["quantity"],
                "price": price
            })
    
    # Determine customer_id - use logged-in customer if available
    customer_id = current_customer.id if current_customer else None
    
    # Create order
    order_number = generate_order_number()
    order = Order(
        order_number=order_number,
        customer_id=customer_id,  # Link to customer account if authenticated
        salon_id=salon_id,
        total_amount=int(total_amount),  # Ensure integer
        status="pending",
        payment_method="flutterwave",
        customer_name=current_customer.name if current_customer else customer_name,
        customer_email=current_customer.email if current_customer else customer_email,
        customer_phone=current_customer.phone if current_customer else customer_phone,
        delivery_address=order_data.get("delivery_address"),
        city=order_data.get("city"),
        notes=order_data.get("notes")
    )
    db.add(order)
    db.flush()
    
    # If customer is authenticated, create SalonCustomer relationship (customer becomes this salon's customer via purchase)
    if current_customer:
        salon_customer = get_or_create_salon_customer(
            db=db,
            salon_id=salon_id,
            customer_id=current_customer.id,
            source="purchase"
        )
        # Update total spent (will be finalized on payment verification)
        salon_customer.last_interaction_at = datetime.utcnow()
    
    # Create order items
    for item_data in order_items:
        if item_data["type"] == "pack":
            order_item = OrderItem(
                order_id=order.id,
                product_id=None,
                pack_id=item_data["pack"].id,
                quantity=item_data["quantity"],
                price_at_purchase=int(item_data["price"])
            )
        else:
            order_item = OrderItem(
                order_id=order.id,
                product_id=item_data["product"].id,
                pack_id=None,
                quantity=item_data["quantity"],
                price_at_purchase=int(item_data["price"])
            )
        db.add(order_item)
    
    db.commit()
    db.refresh(order)
    
    # Return order details for Flutterwave payment
    return {
        "order_id": order.id,
        "order_number": order_number,
        "total_amount": total_amount,
        "customer_email": customer_email,
        "customer_name": customer_name,
        "customer_phone": customer_phone
    }


@router.post("/public/verify/{order_number}")
def verify_public_payment(
    order_number: str,
    verification_data: dict,
    db: Session = Depends(get_db)
):
    """Verify payment from web client and complete order (no authentication required)."""
    # Find order
    order = db.query(Order).filter(
        Order.order_number == order_number
    ).first()
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    if order.status == "paid":
        return {"status": "success", "message": "Payment already verified"}
    
    transaction_id = verification_data.get("transaction_id")
    
    if not transaction_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Transaction ID required"
        )
    
    # Verify with Flutterwave
    verify_url = f"https://api.flutterwave.com/v3/transactions/{transaction_id}/verify"
    headers = {"Authorization": f"Bearer {FLUTTERWAVE_SECRET_KEY}"}
    
    try:
        response = requests.get(verify_url, headers=headers)
        response.raise_for_status()
        flutterwave_data = response.json()
        
        if flutterwave_data["status"] == "success" and flutterwave_data["data"]["status"] == "successful":
            # Verify amount matches
            paid_amount = flutterwave_data["data"]["amount"]
            if abs(paid_amount - order.total_amount) > 0.01:  # Allow small floating point differences
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Payment amount mismatch"
                )
            
            # Update order status
            order.status = "paid"
            order.payment_reference = transaction_id
            order.payment_data = flutterwave_data["data"]
            
            # Reduce product quantities
            for order_item in order.items:
                if order_item.pack_id:
                    # Handle pack - reduce inventory for each product in the pack
                    pack = order_item.pack
                    for pack_product in pack.pack_products:
                        product = pack_product.product
                        required_quantity = pack_product.quantity * order_item.quantity
                        
                        if product.quantity >= required_quantity:
                            product.quantity -= required_quantity
                        else:
                            order.status = "failed"
                            db.commit()
                            raise HTTPException(
                                status_code=status.HTTP_400_BAD_REQUEST,
                                detail=f"Insufficient stock for product '{product.name}' in pack"
                            )
                elif order_item.product_id:
                    # Handle regular product
                    product = order_item.product
                    if product.quantity >= order_item.quantity:
                        product.quantity -= order_item.quantity
                    else:
                        order.status = "failed"
                        db.commit()
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Insufficient stock for product '{product.name}'"
                        )
            
            # Update SalonCustomer total_spent if order has a customer_id
            if order.customer_id:
                salon_customer = db.query(SalonCustomer).filter(
                    SalonCustomer.salon_id == order.salon_id,
                    SalonCustomer.customer_id == order.customer_id
                ).first()
                if salon_customer:
                    salon_customer.total_spent = (salon_customer.total_spent or 0) + order.total_amount
                    salon_customer.last_interaction_at = datetime.utcnow()
            
            db.commit()
            
            # Send notification to salon about order
            try:
                salon = db.query(Salon).filter(Salon.id == order.salon_id).first()
                if salon:
                    items_list = []
                    for item in order.items:
                        if item.product:
                            items_list.append(f"{item.quantity}x {item.product.name}")
                        elif item.pack:
                            items_list.append(f"{item.quantity}x {item.pack.name} (pack)")
                    items_summary = ", ".join(items_list)
                    notification_service = NotificationService(db)
                    notification_service.notify_order_placed(
                        order=order,
                        salon=salon,
                        items_summary=items_summary
                    )
            except Exception as e:
                print(f"[NOTIFICATION ERROR] Failed to send order notification: {e}")
            
            return {
                "status": "success",
                "message": "Payment verified successfully",
                "order_number": order.order_number
            }
        else:
            return {
                "status": "failed",
                "message": "Payment verification failed"
            }
    except requests.exceptions.RequestException as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Payment verification failed: {str(e)}"
        )


@router.patch("/{order_id}/status")
def update_order_status(
    order_id: int,
    status_data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Update order status to delivered or cancelled (salon admin only)."""
    order = db.query(Order).filter(
        Order.id == order_id,
        Order.salon_id == current_user.salon_id
    ).first()
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    new_status = status_data.get("status")
    
    if new_status not in ["delivered", "cancelled"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Status must be 'delivered' or 'cancelled'"
        )
    
    # Only paid orders can be marked as delivered or cancelled
    if order.status != "paid":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only paid orders can be marked as delivered or cancelled"
        )
    
    old_status = order.status
    order.status = new_status
    order.updated_at = datetime.utcnow()
    
    # Log activity
    log = ActivityLog(
        user_id=current_user.id,
        salon_id=current_user.salon_id,
        action="order_status_updated",
        entity_type="order",
        entity_id=order.id,
        details=f"Order {order.order_number} status changed from {old_status} to {new_status}"
    )
    db.add(log)
    db.commit()
    db.refresh(order)
    
    return {
        "status": "success",
        "message": f"Order marked as {new_status}",
        "order": order
    }
