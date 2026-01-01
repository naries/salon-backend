from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from typing import List, Optional
from datetime import datetime, timedelta
from app.core.database import get_db
from app.core.security import get_current_admin_user, get_current_superadmin, get_current_customer
from app.models.models import Appointment, Customer, User, Service, Salon, SubService, ActivityLog, SalonCustomer
from app.schemas.schemas import AppointmentResponse, AppointmentCreate, AvailabilityCheck, AvailabilityResponse, OffsiteQuoteRequest, OffsiteRejectRequest, AppointmentListResponse, AppointmentStatusUpdate
from app.utils.slot_manager import validate_appointment_time, get_slot_availability
from app.api.v1.endpoints.customer_auth import get_or_create_salon_customer
from app.services.notification_service import NotificationService

router = APIRouter()


def auto_cancel_overdue_appointments(db: Session, salon_id: int = None):
    """
    Auto-cancel appointments that are 24+ hours past their scheduled date/time.
    Only affects 'scheduled' appointments.
    """
    cutoff_time = datetime.utcnow() - timedelta(hours=24)
    
    query = db.query(Appointment).filter(
        Appointment.status == "scheduled",
        Appointment.appointment_date < cutoff_time
    )
    
    if salon_id:
        query = query.filter(Appointment.salon_id == salon_id)
    
    overdue_appointments = query.all()
    
    for appointment in overdue_appointments:
        appointment.status = "cancelled"
        # Log the auto-cancellation
        log = ActivityLog(
            user_id=None,
            salon_id=appointment.salon_id,
            action="auto_cancelled",
            entity_type="appointment",
            entity_id=appointment.id,
            description=f"Appointment auto-cancelled - 24+ hours past scheduled time ({appointment.appointment_date.strftime('%Y-%m-%d %H:%M')})"
        )
        db.add(log)
    
    if overdue_appointments:
        db.commit()
    
    return len(overdue_appointments)


@router.get("/", response_model=AppointmentListResponse)
async def get_appointments(
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    search: Optional[str] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Get appointments with pagination and filtering
    - Superadmin: sees all appointments
    - Salon admin: sees only their salon's appointments
    """
    # Auto-cancel overdue appointments before fetching
    salon_id_for_auto_cancel = None if current_user.is_superadmin == 1 else current_user.salon_id
    auto_cancel_overdue_appointments(db, salon_id_for_auto_cancel)
    
    # Base query with eager loading for customer and service
    if current_user.is_superadmin == 1:
        query = db.query(Appointment)
    else:
        query = db.query(Appointment).filter(
            Appointment.salon_id == current_user.salon_id
        )
    
    # Apply search filter (customer name, email, service name)
    if search:
        query = query.outerjoin(Customer, Appointment.customer_id == Customer.id).outerjoin(Service, Appointment.service_id == Service.id).filter(
            or_(
                Customer.name.ilike(f"%{search}%"),
                Customer.email.ilike(f"%{search}%"),
                Service.name.ilike(f"%{search}%")
            )
        )
    
    # Apply status filter
    if status_filter:
        query = query.filter(Appointment.status == status_filter)
    
    # Get total count
    total = query.count()
    
    # Sort by appointment date descending (newest first) and apply pagination
    appointments = query.order_by(Appointment.appointment_date.desc()).offset((page - 1) * per_page).limit(per_page).all()
    
    return {
        "appointments": appointments,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page
    }


@router.get("/salon/{salon_id}", response_model=List[AppointmentResponse])
def get_salon_appointments(
    salon_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superadmin)
):
    """Get appointments for a specific salon (superadmin only)"""
    appointments = db.query(Appointment).filter(
        Appointment.salon_id == salon_id
    ).all()
    return appointments


@router.post("/", response_model=AppointmentResponse, status_code=status.HTTP_201_CREATED)
def create_appointment(
    appointment_data: AppointmentCreate,
    db: Session = Depends(get_db),
    current_customer: Customer = Depends(get_current_customer)
):
    """Create a new appointment with automatic slot assignment and optional sub-service.
    
    For platform-wide customers:
    - salon_id must be provided in the request
    - A SalonCustomer relationship is automatically created
    
    For off-site bookings:
    - Customer must provide offsite_location
    - Status is set to 'pending_review' for salon to review
    - No immediate charge - salon will quote extra charge
    """
    # Determine the salon_id - prefer request data, fall back to customer's legacy salon_id
    salon_id = appointment_data.salon_id or current_customer.salon_id
    if not salon_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="salon_id is required for booking"
        )
    
    # Get the service to check duration
    service = db.query(Service).filter(Service.id == appointment_data.service_id).first()
    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service not found"
        )
    
    # Verify service belongs to the salon
    if service.salon_id != salon_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Service does not belong to this salon"
        )
    
    # Validate sub-service if provided
    sub_service = None
    if appointment_data.sub_service_id:
        sub_service = db.query(SubService).filter(
            SubService.id == appointment_data.sub_service_id,
            SubService.service_id == appointment_data.service_id,
            SubService.is_active == 1
        ).first()
        if not sub_service:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sub-service not found or inactive"
            )
        
        # Validate hours
        if appointment_data.hours and appointment_data.hours <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Hours must be greater than 0"
            )
    
    # Get salon details for slot management
    salon = db.query(Salon).filter(Salon.id == salon_id).first()
    if not salon:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Salon not found"
        )
    
    # Validate off-site booking requirements
    is_offsite = 1 if appointment_data.is_offsite else 0
    if is_offsite and not appointment_data.offsite_location:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Off-site location is required for off-site bookings"
        )
    
    # For off-site bookings, we still validate the time slot
    # but the appointment will be pending review
    is_valid, error_msg, slot_number = validate_appointment_time(
        db=db,
        salon=salon,
        appointment_datetime=appointment_data.appointment_date,
        duration_minutes=service.duration_minutes
    )
    
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg
        )
    
    # Determine initial status based on booking type
    # Off-site bookings start as 'pending_review', regular bookings as 'scheduled'
    initial_status = "pending_review" if is_offsite else "scheduled"
    offsite_status = "pending" if is_offsite else None
    
    # Create appointment with assigned slot and optional sub-service
    db_appointment = Appointment(
        salon_id=salon_id,
        customer_id=current_customer.id,
        service_id=appointment_data.service_id,
        sub_service_id=appointment_data.sub_service_id,
        hours=appointment_data.hours if appointment_data.sub_service_id else 1.0,
        appointment_date=appointment_data.appointment_date,
        slot_number=slot_number,
        notes=appointment_data.notes,
        status=initial_status,
        is_offsite=is_offsite,
        offsite_location=appointment_data.offsite_location if is_offsite else None,
        offsite_status=offsite_status
    )
    db.add(db_appointment)
    db.flush()
    
    # Auto-create salon-customer relationship (customer becomes this salon's customer)
    salon_customer = get_or_create_salon_customer(
        db=db,
        salon_id=salon_id,
        customer_id=current_customer.id,
        source="appointment"
    )
    # Update appointment count
    salon_customer.total_appointments = (salon_customer.total_appointments or 0) + 1
    salon_customer.last_interaction_at = datetime.utcnow()
    
    db.commit()
    db.refresh(db_appointment)
    
    # Log appointment creation
    booking_type = "off-site" if is_offsite else "on-site"
    log = ActivityLog(
        user_id=None,  # Customer appointments don't have a user_id
        salon_id=salon_id,
        action="created",
        entity_type="appointment",
        entity_id=db_appointment.id,
        description=f"Customer {current_customer.name} created {booking_type} appointment on {appointment_data.appointment_date.strftime('%Y-%m-%d %H:%M')}"
    )
    db.add(log)
    db.commit()
    
    # Send notification to salon and customer
    try:
        notification_service = NotificationService(db)
        notification_service.notify_booking_created(
            appointment=db_appointment,
            salon=salon,
            customer=current_customer,
            service=service,
            sub_service=sub_service
        )
    except Exception as e:
        print(f"[NOTIFICATION ERROR] Failed to send booking created notification: {e}")
    
    return db_appointment


@router.get("/my-bookings", response_model=List[AppointmentResponse])
async def get_customer_appointments(
    current_customer: Customer = Depends(get_current_customer),
    db: Session = Depends(get_db)
):
    """Get all appointments for the authenticated customer"""
    appointments = db.query(Appointment).filter(
        Appointment.customer_id == current_customer.id
    ).order_by(Appointment.appointment_date.desc()).all()
    
    return appointments


@router.post("/my-bookings/{appointment_id}/cancel", response_model=AppointmentResponse)
async def customer_cancel_appointment(
    appointment_id: int,
    db: Session = Depends(get_db),
    current_customer: Customer = Depends(get_current_customer)
):
    """
    Cancel an appointment by customer.
    Customers can only cancel their own scheduled appointments.
    """
    appointment = db.query(Appointment).filter(
        Appointment.id == appointment_id,
        Appointment.customer_id == current_customer.id
    ).first()
    
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found"
        )
    
    if appointment.status == "cancelled":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Appointment is already cancelled"
        )
    
    if appointment.status == "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot cancel a completed appointment"
        )
    
    old_status = appointment.status
    appointment.status = "cancelled"
    appointment.status_message = "Cancelled by customer"
    db.commit()
    db.refresh(appointment)
    
    # Log customer cancellation
    log = ActivityLog(
        user_id=None,
        salon_id=appointment.salon_id,
        action="cancelled_by_customer",
        entity_type="appointment",
        entity_id=appointment.id,
        description=f"Customer {current_customer.name} cancelled appointment (was: {old_status})"
    )
    db.add(log)
    db.commit()
    
    # Send notification to salon about customer cancellation
    try:
        salon = db.query(Salon).filter(Salon.id == appointment.salon_id).first()
        service = db.query(Service).filter(Service.id == appointment.service_id).first()
        
        if salon and service:
            notification_service = NotificationService(db)
            notification_service.notify_booking_cancelled_by_customer(
                appointment=appointment,
                salon=salon,
                customer=current_customer,
                service=service
            )
    except Exception as e:
        print(f"[NOTIFICATION ERROR] Failed to send customer cancellation notification: {e}")
    
    return appointment


@router.get("/{appointment_id}", response_model=AppointmentResponse)
def get_appointment(
    appointment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Get appointment by ID (admin only, must be from their salon)"""
    appointment = db.query(Appointment).filter(
        Appointment.id == appointment_id,
        Appointment.salon_id == current_user.salon_id
    ).first()
    
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found"
        )
    return appointment


@router.put("/{appointment_id}", response_model=AppointmentResponse)
def update_appointment(
    appointment_id: int,
    status_update: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Update an appointment status (admin only)"""
    appointment = db.query(Appointment).filter(
        Appointment.id == appointment_id,
        Appointment.salon_id == current_user.salon_id
    ).first()
    
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found"
        )
    
    old_status = appointment.status
    appointment.status = status_update
    db.commit()
    db.refresh(appointment)
    
    # Log appointment update
    log = ActivityLog(
        user_id=current_user.id,
        salon_id=current_user.salon_id,
        action="updated",
        entity_type="appointment",
        entity_id=appointment.id,
        description=f"Updated appointment status from {old_status} to {status_update}",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    db.add(log)
    db.commit()
    
    return appointment


@router.delete("/{appointment_id}")
def delete_appointment(
    appointment_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Delete an appointment (admin only)"""
    appointment = db.query(Appointment).filter(
        Appointment.id == appointment_id,
        Appointment.salon_id == current_user.salon_id
    ).first()
    
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found"
        )
    
    appointment_date = appointment.appointment_date
    db.delete(appointment)
    db.commit()
    
    # Log appointment deletion
    log = ActivityLog(
        user_id=current_user.id,
        salon_id=current_user.salon_id,
        action="deleted",
        entity_type="appointment",
        entity_id=appointment_id,
        description=f"Deleted appointment scheduled for {appointment_date.strftime('%Y-%m-%d %H:%M')}",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    db.add(log)
    db.commit()
    
    return {"message": "Appointment deleted"}


@router.post("/{appointment_id}/complete", response_model=AppointmentResponse)
def complete_appointment(
    appointment_id: int,
    status_update: AppointmentStatusUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Mark an appointment as completed (salon admin only)"""
    appointment = db.query(Appointment).filter(
        Appointment.id == appointment_id,
        Appointment.salon_id == current_user.salon_id
    ).first()
    
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found"
        )
    
    if appointment.status == "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Appointment is already completed"
        )
    
    if appointment.status == "cancelled":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot complete a cancelled appointment"
        )
    
    old_status = appointment.status
    appointment.status = "completed"
    appointment.status_message = status_update.message
    db.commit()
    db.refresh(appointment)
    
    # Log appointment completion
    log = ActivityLog(
        user_id=current_user.id,
        salon_id=current_user.salon_id,
        action="completed",
        entity_type="appointment",
        entity_id=appointment.id,
        description=f"Marked appointment as completed (was: {old_status}). Message: {status_update.message[:100]}...",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    db.add(log)
    db.commit()
    
    return appointment


@router.post("/{appointment_id}/cancel", response_model=AppointmentResponse)
def cancel_appointment(
    appointment_id: int,
    status_update: AppointmentStatusUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Cancel an appointment (salon admin only)"""
    appointment = db.query(Appointment).filter(
        Appointment.id == appointment_id,
        Appointment.salon_id == current_user.salon_id
    ).first()
    
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found"
        )
    
    if appointment.status == "cancelled":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Appointment is already cancelled"
        )
    
    if appointment.status == "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot cancel a completed appointment"
        )
    
    old_status = appointment.status
    appointment.status = "cancelled"
    appointment.status_message = status_update.message
    db.commit()
    db.refresh(appointment)
    
    # Log appointment cancellation
    log = ActivityLog(
        user_id=current_user.id,
        salon_id=current_user.salon_id,
        action="cancelled",
        entity_type="appointment",
        entity_id=appointment.id,
        description=f"Cancelled appointment (was: {old_status}). Message: {status_update.message[:100]}...",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    db.add(log)
    db.commit()
    
    # Send notification to customer about cancellation
    try:
        salon = db.query(Salon).filter(Salon.id == appointment.salon_id).first()
        customer = db.query(Customer).filter(Customer.id == appointment.customer_id).first()
        service = db.query(Service).filter(Service.id == appointment.service_id).first()
        
        if salon and customer and service:
            notification_service = NotificationService(db)
            notification_service.notify_booking_cancelled_by_salon(
                appointment=appointment,
                salon=salon,
                customer=customer,
                service=service,
                reason=status_update.message
            )
    except Exception as e:
        print(f"[NOTIFICATION ERROR] Failed to send cancellation notification: {e}")
    
    return appointment


@router.post("/check-availability", response_model=AvailabilityResponse)
def check_availability(
    availability_check: AvailabilityCheck,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Check if a time slot is available for booking"""
    # Get the service to check duration
    service = db.query(Service).filter(Service.id == availability_check.service_id).first()
    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service not found"
        )
    
    # Get salon details
    salon = db.query(Salon).filter(Salon.id == current_user.salon_id).first()
    if not salon:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Salon not found"
        )
    
    # Validate and get slot
    is_valid, error_msg, slot_number = validate_appointment_time(
        db=db,
        salon=salon,
        appointment_datetime=availability_check.appointment_date,
        duration_minutes=service.duration_minutes
    )
    
    return AvailabilityResponse(
        is_available=is_valid,
        slot_number=slot_number,
        error_message=error_msg
    )


@router.get("/available-slots/{salon_slug}/{service_id}")
def get_available_slots_public(
    salon_slug: str,
    service_id: int,
    date: str,  # ISO format date string
    db: Session = Depends(get_db)
):
    """Public endpoint to get all available time slots for a specific date and service"""
    # Get salon
    salon = db.query(Salon).filter(Salon.slug == salon_slug, Salon.is_active == 1).first()
    if not salon:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Salon not found"
        )
    
    # Get service
    service = db.query(Service).filter(Service.id == service_id, Service.salon_id == salon.id).first()
    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service not found"
        )
    
    # Parse date
    try:
        target_date = datetime.fromisoformat(date)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid date format. Use ISO format (YYYY-MM-DD)"
        )
    
    # Get available slots
    available_slots = get_slot_availability(
        db=db,
        salon=salon,
        target_date=target_date,
        duration_minutes=service.duration_minutes
    )
    
    return {
        "salon": {"name": salon.name, "slug": salon.slug},
        "service": {"id": service.id, "name": service.name, "duration_minutes": service.duration_minutes},
        "date": date,
        "opening_hour": salon.opening_hour,
        "closing_hour": salon.closing_hour,
        "max_concurrent_slots": salon.max_concurrent_slots,
        "available_slots": available_slots
    }


@router.get("/date-availability/{salon_slug}/{service_id}")
def get_date_availability(
    salon_slug: str,
    service_id: int,
    month: int,
    year: int,
    db: Session = Depends(get_db)
):
    """Get availability status for all dates in a month"""
    # Get salon
    salon = db.query(Salon).filter(Salon.slug == salon_slug, Salon.is_active == 1).first()
    if not salon:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Salon not found"
        )
    
    # Get service
    service = db.query(Service).filter(Service.id == service_id, Service.salon_id == salon.id).first()
    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service not found"
        )
    
    # Validate month and year
    if month < 1 or month > 12:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid month. Must be between 1 and 12"
        )
    
    if year < 2020 or year > 2030:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid year. Must be between 2020 and 2030"
        )
    
    # Calculate days in month
    import calendar
    days_in_month = calendar.monthrange(year, month)[1]
    
    availability_data = {}
    
    # Check each day in the month
    for day in range(1, days_in_month + 1):
        try:
            target_date = datetime(year, month, day)
            
            # Skip past dates
            if target_date.date() < datetime.now().date():
                availability_data[target_date.date().isoformat()] = {
                    "available": False,
                    "reason": "past_date"
                }
                continue
            
            # Get available slots for this date
            available_slots = get_slot_availability(
                db=db,
                salon=salon,
                target_date=target_date,
                duration_minutes=service.duration_minutes
            )
            
            availability_data[target_date.date().isoformat()] = {
                "available": len(available_slots) > 0,
                "total_slots": len(available_slots),
                "reason": "no_slots" if len(available_slots) == 0 else "available"
            }
            
        except Exception as e:
            # Skip invalid dates (like Feb 30)
            continue
    
    return {
        "salon": {"name": salon.name, "slug": salon.slug},
        "service": {"id": service.id, "name": service.name},
        "month": month,
        "year": year,
        "availability": availability_data
    }


# ==================== Off-Site Booking Management ====================

@router.get("/offsite-requests", response_model=List[AppointmentResponse])
def get_offsite_requests(
    status_filter: Optional[str] = Query(None, alias="status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Get all off-site booking requests for the salon (admin only)"""
    query = db.query(Appointment).filter(
        Appointment.salon_id == current_user.salon_id,
        Appointment.is_offsite == 1
    )
    
    # Filter by offsite_status if provided
    if status_filter:
        query = query.filter(Appointment.offsite_status == status_filter)
    
    appointments = query.order_by(Appointment.created_at.desc()).all()
    return appointments


@router.post("/{appointment_id}/quote-offsite", response_model=AppointmentResponse)
def quote_offsite_appointment(
    appointment_id: int,
    quote_data: OffsiteQuoteRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Quote an extra charge for an off-site appointment (admin only)
    
    This allows the salon to provide a quote for the extra travel/service charge.
    The customer will need to accept this quote before the appointment is confirmed.
    """
    appointment = db.query(Appointment).filter(
        Appointment.id == appointment_id,
        Appointment.salon_id == current_user.salon_id,
        Appointment.is_offsite == 1
    ).first()
    
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Off-site appointment not found"
        )
    
    if appointment.offsite_status not in ["pending", None]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot quote appointment with status: {appointment.offsite_status}"
        )
    
    if quote_data.extra_charge < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Extra charge cannot be negative"
        )
    
    # Update appointment with quote
    appointment.offsite_extra_charge = quote_data.extra_charge
    appointment.offsite_response = quote_data.response
    appointment.offsite_status = "quoted"
    appointment.offsite_responded_at = datetime.utcnow()
    appointment.status = "pending_customer"  # Waiting for customer to accept/reject quote
    
    db.commit()
    db.refresh(appointment)
    
    # Log the action
    log = ActivityLog(
        user_id=current_user.id,
        salon_id=current_user.salon_id,
        action="quoted",
        entity_type="appointment",
        entity_id=appointment.id,
        description=f"Quoted off-site appointment with extra charge of ₦{quote_data.extra_charge / 100:.2f}",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    db.add(log)
    db.commit()
    
    return appointment


@router.post("/{appointment_id}/reject-offsite", response_model=AppointmentResponse)
def reject_offsite_appointment(
    appointment_id: int,
    reject_data: OffsiteRejectRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Reject an off-site appointment request (admin only)
    
    This allows the salon to decline the off-site booking request.
    """
    appointment = db.query(Appointment).filter(
        Appointment.id == appointment_id,
        Appointment.salon_id == current_user.salon_id,
        Appointment.is_offsite == 1
    ).first()
    
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Off-site appointment not found"
        )
    
    if appointment.offsite_status not in ["pending", None]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot reject appointment with status: {appointment.offsite_status}"
        )
    
    # Update appointment as rejected
    appointment.offsite_response = reject_data.response
    appointment.offsite_status = "rejected"
    appointment.offsite_responded_at = datetime.utcnow()
    appointment.status = "cancelled"
    
    db.commit()
    db.refresh(appointment)
    
    # Log the action
    log = ActivityLog(
        user_id=current_user.id,
        salon_id=current_user.salon_id,
        action="rejected",
        entity_type="appointment",
        entity_id=appointment.id,
        description=f"Rejected off-site appointment request: {reject_data.response}",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    db.add(log)
    db.commit()
    
    return appointment


@router.post("/{appointment_id}/accept-quote", response_model=AppointmentResponse)
def accept_offsite_quote(
    appointment_id: int,
    db: Session = Depends(get_db),
    current_customer: Customer = Depends(get_current_customer)
):
    """Accept the quoted extra charge for an off-site appointment (customer only)
    
    Once accepted, the appointment status changes to 'scheduled'.
    """
    appointment = db.query(Appointment).filter(
        Appointment.id == appointment_id,
        Appointment.customer_id == current_customer.id,
        Appointment.is_offsite == 1
    ).first()
    
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Off-site appointment not found"
        )
    
    if appointment.offsite_status != "quoted":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No quote available to accept"
        )
    
    # Accept the quote
    appointment.offsite_status = "accepted"
    appointment.status = "scheduled"
    
    db.commit()
    db.refresh(appointment)
    
    # Log the action
    log = ActivityLog(
        user_id=None,
        salon_id=appointment.salon_id,
        action="accepted",
        entity_type="appointment",
        entity_id=appointment.id,
        description=f"Customer accepted off-site quote of ₦{appointment.offsite_extra_charge / 100:.2f}"
    )
    db.add(log)
    db.commit()
    
    return appointment


@router.post("/{appointment_id}/reject-quote", response_model=AppointmentResponse)
def reject_offsite_quote(
    appointment_id: int,
    db: Session = Depends(get_db),
    current_customer: Customer = Depends(get_current_customer)
):
    """Reject the quoted extra charge for an off-site appointment (customer only)
    
    The appointment will be cancelled if the customer rejects the quote.
    """
    appointment = db.query(Appointment).filter(
        Appointment.id == appointment_id,
        Appointment.customer_id == current_customer.id,
        Appointment.is_offsite == 1
    ).first()
    
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Off-site appointment not found"
        )
    
    if appointment.offsite_status != "quoted":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No quote available to reject"
        )
    
    # Reject the quote and cancel appointment
    appointment.offsite_status = "quote_rejected"
    appointment.status = "cancelled"
    
    db.commit()
    db.refresh(appointment)
    
    # Log the action
    log = ActivityLog(
        user_id=None,
        salon_id=appointment.salon_id,
        action="quote_rejected",
        entity_type="appointment",
        entity_id=appointment.id,
        description=f"Customer rejected off-site quote of ₦{appointment.offsite_extra_charge / 100:.2f}"
    )
    db.add(log)
    db.commit()
    
    return appointment
