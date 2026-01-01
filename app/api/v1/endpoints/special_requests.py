from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from app.core.database import get_db
from app.core.security import get_current_admin_user, get_current_customer
from app.models.models import SpecialRequest, Customer, User, Service, Salon, ActivityLog, SalonCustomer
from app.schemas.schemas import SpecialRequestCreate, SpecialRequestQuote, SpecialRequestReject, SpecialRequestResponse
from app.api.v1.endpoints.customer_auth import get_or_create_salon_customer
from app.services.notification_service import NotificationService

router = APIRouter()


@router.post("/", response_model=SpecialRequestResponse, status_code=status.HTTP_201_CREATED)
def create_special_request(
    request_data: SpecialRequestCreate,
    db: Session = Depends(get_db),
    current_customer: Customer = Depends(get_current_customer)
):
    """Create a new special request - customer describes what they want.
    
    For platform-wide customers, salon_id must be provided in the request.
    The salon will review and provide a quote with suggested products.
    """
    # Determine the salon_id - prefer request data, fall back to customer's legacy salon_id
    salon_id = request_data.salon_id or current_customer.salon_id
    if not salon_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="salon_id is required for special requests"
        )
    
    # Validate service if provided
    if request_data.service_id:
        service = db.query(Service).filter(
            Service.id == request_data.service_id,
            Service.salon_id == salon_id
        ).first()
        if not service:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Service not found"
            )
    
    # Validate off-site requirements
    if request_data.is_offsite and not request_data.offsite_location:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Off-site location is required for off-site requests"
        )
    
    # Handle media_ids (new preferred method)
    image_file_ids = request_data.image_file_ids
    if request_data.media_ids:
        from app.models.models import MediaUpload, CloudFile
        
        file_ids = []
        for media_id in request_data.media_ids:
            # Fetch MediaUpload record
            media_upload = db.query(MediaUpload).filter(
                MediaUpload.id == media_id,
                MediaUpload.status == "completed"
            ).first()
            
            if media_upload:
                # Create CloudFile from media upload
                cloud_file = CloudFile(
                    filename=media_upload.original_filename,
                    file_path=media_upload.public_url or media_upload.gcs_path,
                    file_type=media_upload.file_type,
                    file_size=media_upload.file_size,
                    uploaded_by=current_customer.id
                )
                db.add(cloud_file)
                db.flush()
                file_ids.append(str(cloud_file.id))
        
        if file_ids:
            image_file_ids = ','.join(file_ids)
    
    # Create the special request
    db_request = SpecialRequest(
        salon_id=salon_id,
        customer_id=current_customer.id,
        service_id=request_data.service_id,
        customer_name=request_data.customer_name,
        customer_email=request_data.customer_email,
        customer_phone=request_data.customer_phone,
        description=request_data.description,
        is_offsite=request_data.is_offsite or 0,
        offsite_location=request_data.offsite_location,
        preferred_date=request_data.preferred_date,
        image_file_ids=image_file_ids,
        status="pending"
    )
    db.add(db_request)
    db.flush()
    
    # Auto-create salon-customer relationship
    get_or_create_salon_customer(
        db=db,
        salon_id=salon_id,
        customer_id=current_customer.id,
        source="appointment"  # Special requests are like appointment requests
    )
    
    # Log the creation
    log = ActivityLog(
        user_id=None,
        salon_id=salon_id,
        action="created",
        entity_type="special_request",
        entity_id=db_request.id,
        description=f"Customer {request_data.customer_name} created a special request"
    )
    db.add(log)
    db.commit()
    db.refresh(db_request)
    
    # Send notification to salon about special request
    try:
        salon = db.query(Salon).filter(Salon.id == salon_id).first()
        if salon:
            notification_service = NotificationService(db)
            notification_service.notify_special_request_received(
                request=db_request,
                salon=salon,
                customer=current_customer
            )
    except Exception as e:
        print(f"[NOTIFICATION ERROR] Failed to send special request notification: {e}")
    
    return db_request


@router.get("/my-requests", response_model=List[SpecialRequestResponse])
def get_customer_special_requests(
    db: Session = Depends(get_db),
    current_customer: Customer = Depends(get_current_customer)
):
    """Get all special requests for the authenticated customer"""
    requests = db.query(SpecialRequest).filter(
        SpecialRequest.customer_id == current_customer.id
    ).order_by(SpecialRequest.created_at.desc()).all()
    
    return requests


@router.get("/salon-requests", response_model=List[SpecialRequestResponse])
def get_salon_special_requests(
    status_filter: Optional[str] = Query(None, alias="status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Get all special requests for the salon (admin only)"""
    query = db.query(SpecialRequest).filter(
        SpecialRequest.salon_id == current_user.salon_id
    )
    
    if status_filter:
        query = query.filter(SpecialRequest.status == status_filter)
    
    requests = query.order_by(SpecialRequest.created_at.desc()).all()
    return requests


@router.get("/{request_id}", response_model=SpecialRequestResponse)
def get_special_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_customer: Customer = Depends(get_current_customer)
):
    """Get a specific special request by ID (customer only, must own the request)"""
    special_request = db.query(SpecialRequest).filter(
        SpecialRequest.id == request_id,
        SpecialRequest.customer_id == current_customer.id
    ).first()
    
    if not special_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Special request not found"
        )
    
    return special_request


@router.post("/{request_id}/quote", response_model=SpecialRequestResponse)
def quote_special_request(
    request_id: int,
    quote_data: SpecialRequestQuote,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Provide a quote for a special request (admin only)
    
    The salon can quote an amount and suggest products to fulfill the request.
    """
    special_request = db.query(SpecialRequest).filter(
        SpecialRequest.id == request_id,
        SpecialRequest.salon_id == current_user.salon_id
    ).first()
    
    if not special_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Special request not found"
        )
    
    if special_request.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot quote request with status: {special_request.status}"
        )
    
    # Update with quote
    special_request.quoted_amount = quote_data.quoted_amount
    special_request.quoted_products = quote_data.quoted_products
    special_request.salon_notes = quote_data.salon_notes
    special_request.quoted_at = datetime.utcnow()
    special_request.status = "quoted"
    special_request.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(special_request)
    
    # Log the action
    log = ActivityLog(
        user_id=current_user.id,
        salon_id=current_user.salon_id,
        action="quoted",
        entity_type="special_request",
        entity_id=special_request.id,
        description=f"Quoted special request at ₦{quote_data.quoted_amount / 100:.2f}",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    db.add(log)
    db.commit()
    
    # Send notification to customer about quote
    try:
        salon = db.query(Salon).filter(Salon.id == special_request.salon_id).first()
        customer = db.query(Customer).filter(Customer.id == special_request.customer_id).first()
        if salon and customer:
            notification_service = NotificationService(db)
            notification_service.notify_special_request_quoted(
                request=special_request,
                salon=salon,
                customer=customer
            )
    except Exception as e:
        print(f"[NOTIFICATION ERROR] Failed to send quote notification: {e}")
    
    return special_request


@router.post("/{request_id}/reject", response_model=SpecialRequestResponse)
def reject_special_request(
    request_id: int,
    reject_data: SpecialRequestReject,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Reject a special request (admin only)"""
    special_request = db.query(SpecialRequest).filter(
        SpecialRequest.id == request_id,
        SpecialRequest.salon_id == current_user.salon_id
    ).first()
    
    if not special_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Special request not found"
        )
    
    if special_request.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot reject request with status: {special_request.status}"
        )
    
    # Update as rejected
    special_request.salon_notes = reject_data.salon_notes
    special_request.status = "rejected"
    special_request.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(special_request)
    
    # Log the action
    log = ActivityLog(
        user_id=current_user.id,
        salon_id=current_user.salon_id,
        action="rejected",
        entity_type="special_request",
        entity_id=special_request.id,
        description=f"Rejected special request: {reject_data.salon_notes}",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    db.add(log)
    db.commit()
    
    return special_request


@router.post("/{request_id}/accept-quote", response_model=SpecialRequestResponse)
def accept_quote(
    request_id: int,
    db: Session = Depends(get_db),
    current_customer: Customer = Depends(get_current_customer)
):
    """Accept a quote for a special request (customer only)"""
    special_request = db.query(SpecialRequest).filter(
        SpecialRequest.id == request_id,
        SpecialRequest.customer_id == current_customer.id
    ).first()
    
    if not special_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Special request not found"
        )
    
    if special_request.status != "quoted":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No quote available to accept"
        )
    
    # Accept the quote
    special_request.status = "accepted"
    special_request.responded_at = datetime.utcnow()
    special_request.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(special_request)
    
    # Log the action
    log = ActivityLog(
        user_id=None,
        salon_id=special_request.salon_id,
        action="accepted",
        entity_type="special_request",
        entity_id=special_request.id,
        description=f"Customer accepted quote of ₦{special_request.quoted_amount / 100:.2f}"
    )
    db.add(log)
    db.commit()
    
    return special_request


@router.post("/{request_id}/reject-quote", response_model=SpecialRequestResponse)
def reject_quote(
    request_id: int,
    db: Session = Depends(get_db),
    current_customer: Customer = Depends(get_current_customer)
):
    """Reject a quote for a special request (customer only)"""
    special_request = db.query(SpecialRequest).filter(
        SpecialRequest.id == request_id,
        SpecialRequest.customer_id == current_customer.id
    ).first()
    
    if not special_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Special request not found"
        )
    
    if special_request.status != "quoted":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No quote available to reject"
        )
    
    # Reject the quote - set back to pending so salon can re-quote
    special_request.customer_response = "Quote rejected by customer"
    special_request.responded_at = datetime.utcnow()
    special_request.status = "cancelled"
    special_request.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(special_request)
    
    # Log the action
    log = ActivityLog(
        user_id=None,
        salon_id=special_request.salon_id,
        action="quote_rejected",
        entity_type="special_request",
        entity_id=special_request.id,
        description=f"Customer rejected quote of ₦{special_request.quoted_amount / 100:.2f}"
    )
    db.add(log)
    db.commit()
    
    return special_request
