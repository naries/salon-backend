from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, date
from typing import Dict

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import User, Appointment, Customer, Service, Salon

router = APIRouter()


@router.get("/stats", response_model=Dict)
async def get_dashboard_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get dashboard statistics for current user
    - Salon admin: salon-specific stats
    - Superadmin: platform-wide stats
    """
    
    # Superadmin gets platform-wide statistics
    if current_user.is_superadmin == 1:
        # Total registered salons
        total_salons = db.query(func.count(Salon.id)).filter(
            Salon.deleted_at.is_(None)
        ).scalar() or 0
        
        # Active salons
        active_salons = db.query(func.count(Salon.id)).filter(
            Salon.deleted_at.is_(None),
            Salon.is_active == 1
        ).scalar() or 0
        
        # Inactive salons
        inactive_salons = db.query(func.count(Salon.id)).filter(
            Salon.deleted_at.is_(None),
            Salon.is_active == 0
        ).scalar() or 0
        
        # Total appointments across all salons
        total_appointments = db.query(func.count(Appointment.id)).scalar() or 0
        
        return {
            "total_salons": total_salons,
            "active_salons": active_salons,
            "inactive_salons": inactive_salons,
            "total_appointments": total_appointments
        }
    
    # Salon admin gets salon-specific statistics
    salon_id = current_user.salon_id
    today = date.today()
    
    # Today's appointments count
    today_appointments = db.query(func.count(Appointment.id)).filter(
        Appointment.salon_id == salon_id,
        func.date(Appointment.appointment_date) == today
    ).scalar() or 0
    
    # Total customers count for this salon
    total_customers = db.query(func.count(Customer.id)).filter(
        Customer.salon_id == salon_id
    ).scalar() or 0
    
    # Active services count
    active_services = db.query(func.count(Service.id)).filter(
        Service.salon_id == salon_id
    ).scalar() or 0
    
    # Today's revenue from completed appointments
    today_completed = db.query(Appointment).filter(
        Appointment.salon_id == salon_id,
        func.date(Appointment.appointment_date) == today,
        Appointment.status == "completed"
    ).all()
    
    today_revenue = 0
    for appointment in today_completed:
        if appointment.sub_service:
            today_revenue += int(appointment.sub_service.hourly_rate * appointment.hours)
        elif appointment.service and appointment.service.price:
            today_revenue += appointment.service.price
    
    return {
        "today_appointments": today_appointments,
        "total_customers": total_customers,
        "active_services": active_services,
        "today_revenue": today_revenue  # in kobo (cents)
    }
