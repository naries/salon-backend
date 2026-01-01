"""
Slot management utilities for multi-slot booking system.

Each salon can have multiple concurrent slots (calendars) that allow
parallel bookings. The system automatically assigns appointments to
available slots based on time conflicts.
"""
from datetime import datetime, timedelta
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from app.models.models import Salon, Appointment, Service


def is_within_salon_hours(salon: Salon, appointment_datetime: datetime) -> bool:
    """
    Check if the appointment time is within salon operating hours.
    
    Args:
        salon: The salon object with opening_hour and closing_hour
        appointment_datetime: The requested appointment datetime
        
    Returns:
        True if within hours, False otherwise
    """
    appointment_hour = appointment_datetime.hour
    
    # Check if appointment starts within operating hours
    if appointment_hour < salon.opening_hour or appointment_hour >= salon.closing_hour:
        return False
    
    return True


def get_appointment_end_time(appointment_start: datetime, duration_minutes: int) -> datetime:
    """Calculate when an appointment ends."""
    return appointment_start + timedelta(minutes=duration_minutes)


def check_time_conflict(start1: datetime, end1: datetime, start2: datetime, end2: datetime) -> bool:
    """
    Check if two time ranges overlap.
    
    Returns:
        True if there's a conflict (overlap), False otherwise
    """
    # No conflict if one ends before the other starts
    if end1 <= start2 or end2 <= start1:
        return False
    return True


def find_available_slot(
    db: Session,
    salon_id: int,
    appointment_start: datetime,
    duration_minutes: int,
    max_slots: int
) -> Optional[int]:
    """
    Find the first available slot for a given time range.
    
    Checks each slot (1 to max_slots) and returns the first one
    without time conflicts. Returns None if all slots are booked.
    
    Args:
        db: Database session
        salon_id: ID of the salon
        appointment_start: Start time of the requested appointment
        duration_minutes: Duration of the service in minutes
        max_slots: Maximum number of concurrent slots available
        
    Returns:
        Slot number (1-based) if available, None if fully booked
    """
    appointment_end = get_appointment_end_time(appointment_start, duration_minutes)
    appointment_date = appointment_start.date()
    
    # Check each slot
    for slot_num in range(1, max_slots + 1):
        # Get all active appointments for this salon, slot, and date
        existing_appointments = db.query(Appointment).join(Service).filter(
            Appointment.salon_id == salon_id,
            Appointment.slot_number == slot_num,
            Appointment.status.in_(["scheduled", "confirmed"]),
            Appointment.appointment_date >= datetime.combine(appointment_date, datetime.min.time()),
            Appointment.appointment_date < datetime.combine(appointment_date + timedelta(days=1), datetime.min.time())
        ).all()
        
        # Check for conflicts with existing appointments in this slot
        has_conflict = False
        for existing in existing_appointments:
            existing_start = existing.appointment_date
            existing_end = get_appointment_end_time(existing_start, existing.service.duration_minutes)
            
            if check_time_conflict(appointment_start, appointment_end, existing_start, existing_end):
                has_conflict = True
                break
        
        # If no conflict found in this slot, it's available
        if not has_conflict:
            return slot_num
    
    # All slots are booked
    return None


def get_slot_availability(
    db: Session,
    salon: Salon,
    target_date: datetime,
    duration_minutes: int
) -> List[dict]:
    """
    Get all available time slots for a given date.
    
    Returns a list of available times with their slot numbers.
    
    Args:
        db: Database session
        salon: The salon object
        target_date: The date to check (should be date at midnight)
        duration_minutes: Duration needed for the service
        
    Returns:
        List of dicts with 'time' and 'slot_number' keys
    """
    available_times = []
    
    # Generate time slots from opening to closing hour
    # Using 30-minute intervals as default
    current_time = target_date.replace(hour=salon.opening_hour, minute=0, second=0, microsecond=0)
    closing_time = target_date.replace(hour=salon.closing_hour, minute=0, second=0, microsecond=0)
    
    # Make sure appointment can finish before closing
    last_start_time = closing_time - timedelta(minutes=duration_minutes)
    
    while current_time <= last_start_time:
        slot_number = find_available_slot(
            db=db,
            salon_id=salon.id,
            appointment_start=current_time,
            duration_minutes=duration_minutes,
            max_slots=salon.max_concurrent_slots
        )
        
        if slot_number is not None:
            available_times.append({
                'time': current_time.isoformat(),
                'slot_number': slot_number,
                'available': True
            })
        
        # Move to next 30-minute interval
        current_time += timedelta(minutes=30)
    
    return available_times


def validate_appointment_time(
    db: Session,
    salon: Salon,
    appointment_datetime: datetime,
    duration_minutes: int
) -> Tuple[bool, Optional[str], Optional[int]]:
    """
    Validate if an appointment can be booked at the requested time.
    
    Returns:
        Tuple of (is_valid, error_message, assigned_slot_number)
    """
    # Check if within salon hours
    if not is_within_salon_hours(salon, appointment_datetime):
        return False, f"Appointment time must be between {salon.opening_hour}:00 and {salon.closing_hour}:00", None
    
    # Check if appointment would end before closing time
    appointment_end = get_appointment_end_time(appointment_datetime, duration_minutes)
    closing_datetime = appointment_datetime.replace(hour=salon.closing_hour, minute=0, second=0, microsecond=0)
    
    if appointment_end > closing_datetime:
        return False, f"Appointment would extend beyond closing time ({salon.closing_hour}:00)", None
    
    # Find available slot
    slot_number = find_available_slot(
        db=db,
        salon_id=salon.id,
        appointment_start=appointment_datetime,
        duration_minutes=duration_minutes,
        max_slots=salon.max_concurrent_slots
    )
    
    if slot_number is None:
        return False, "All slots are fully booked for this time", None
    
    return True, None, slot_number
