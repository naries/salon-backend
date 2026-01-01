from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import User
from pydantic import BaseModel

router = APIRouter()


class ThemeUpdate(BaseModel):
    theme_name: str


@router.get("/me")
def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information including theme preference"""
    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "is_admin": current_user.is_admin,
        "is_superadmin": current_user.is_superadmin,
        "salon_id": current_user.salon_id,
        "theme_name": current_user.theme_name or "purple"
    }


@router.put("/theme")
def update_user_theme(
    theme_update: ThemeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update user's theme preference"""
    # Valid theme names
    valid_themes = ["purple", "blue", "green", "rose", "amber", "teal", "indigo", "slate"]
    
    if theme_update.theme_name not in valid_themes:
        raise HTTPException(status_code=400, detail="Invalid theme name")
    
    current_user.theme_name = theme_update.theme_name
    db.commit()
    db.refresh(current_user)
    
    return {
        "message": "Theme updated successfully",
        "theme_name": current_user.theme_name
    }
