from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict

from app.core.database import get_db
from app.core.security import get_current_superadmin, get_current_user
from app.models.models import SuperadminSettings, User

router = APIRouter()


@router.get("/public", response_model=Dict)
async def get_public_settings(db: Session = Depends(get_db)):
    """
    Get public superadmin settings (no authentication required)
    Used for login/register pages
    """
    settings = db.query(SuperadminSettings).first()
    
    if not settings:
        return {
            "default_logo_icon": "scissors"
        }
    
    return {
        "default_logo_icon": settings.default_logo_icon
    }


@router.get("/", response_model=Dict)
async def get_superadmin_settings(
    current_user: User = Depends(get_current_superadmin),
    db: Session = Depends(get_db)
):
    """
    Get superadmin default settings
    """
    settings = db.query(SuperadminSettings).first()
    
    if not settings:
        # Create default settings if none exist
        settings = SuperadminSettings()
        db.add(settings)
        db.commit()
        db.refresh(settings)
    
    return {
        "default_logo_icon": settings.default_logo_icon,
        "default_opening_hour": settings.default_opening_hour,
        "default_closing_hour": settings.default_closing_hour,
        "default_max_concurrent_slots": settings.default_max_concurrent_slots
    }


@router.put("/", response_model=Dict)
async def update_superadmin_settings(
    settings_data: Dict,
    current_user: User = Depends(get_current_superadmin),
    db: Session = Depends(get_db)
):
    """
    Update superadmin default settings
    """
    settings = db.query(SuperadminSettings).first()
    
    if not settings:
        settings = SuperadminSettings()
        db.add(settings)
    
    # Update fields if provided
    if "default_logo_icon" in settings_data:
        settings.default_logo_icon = settings_data["default_logo_icon"]
    if "default_opening_hour" in settings_data:
        settings.default_opening_hour = settings_data["default_opening_hour"]
    if "default_closing_hour" in settings_data:
        settings.default_closing_hour = settings_data["default_closing_hour"]
    if "default_max_concurrent_slots" in settings_data:
        settings.default_max_concurrent_slots = settings_data["default_max_concurrent_slots"]
    
    db.commit()
    db.refresh(settings)
    
    return {
        "message": "Settings updated successfully",
        "settings": {
            "default_logo_icon": settings.default_logo_icon,
            "default_opening_hour": settings.default_opening_hour,
            "default_closing_hour": settings.default_closing_hour,
            "default_max_concurrent_slots": settings.default_max_concurrent_slots
        }
    }
