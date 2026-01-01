"""
Customer Favorites API endpoints
Allows customers to favorite/unfavorite salons
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from typing import List
from pydantic import BaseModel
from app.core.database import get_db
from app.core.security import get_current_customer
from app.models.models import Customer, Salon, CustomerFavoriteSalon

router = APIRouter()


class FavoriteResponse(BaseModel):
    id: int
    salon_id: int
    created_at: str
    
    class Config:
        from_attributes = True


class SalonBasicInfo(BaseModel):
    id: int
    name: str
    slug: str
    address: str | None = None
    logo_url: str | None = None
    
    class Config:
        from_attributes = True


class FavoriteWithSalon(BaseModel):
    id: int
    salon_id: int
    salon: SalonBasicInfo
    created_at: str
    
    class Config:
        from_attributes = True


@router.get("/", response_model=List[dict])
async def get_favorites(
    db: Session = Depends(get_db),
    current_customer: Customer = Depends(get_current_customer)
):
    """
    Get all favorited salons for the current customer.
    """
    favorites = db.query(CustomerFavoriteSalon).filter(
        CustomerFavoriteSalon.customer_id == current_customer.id
    ).options(
        joinedload(CustomerFavoriteSalon.salon)
    ).order_by(CustomerFavoriteSalon.created_at.desc()).all()
    
    result = []
    for fav in favorites:
        salon = fav.salon
        # Build logo URL
        logo_url = None
        if salon.logo_file_id and salon.logo_file:
            logo_url = salon.logo_file.public_url
        
        result.append({
            "id": fav.id,
            "salon_id": fav.salon_id,
            "created_at": fav.created_at.isoformat() if fav.created_at else None,
            "salon": {
                "id": salon.id,
                "name": salon.name,
                "slug": salon.slug,
                "address": salon.address,
                "logo_url": logo_url,
                "phone": salon.phone,
            }
        })
    
    return result


@router.get("/ids")
async def get_favorite_ids(
    db: Session = Depends(get_db),
    current_customer: Customer = Depends(get_current_customer)
):
    """
    Get just the salon IDs that are favorited (for quick lookup).
    """
    favorites = db.query(CustomerFavoriteSalon.salon_id).filter(
        CustomerFavoriteSalon.customer_id == current_customer.id
    ).all()
    
    return {"salon_ids": [f.salon_id for f in favorites]}


@router.post("/{salon_id}")
async def add_favorite(
    salon_id: int,
    db: Session = Depends(get_db),
    current_customer: Customer = Depends(get_current_customer)
):
    """
    Add a salon to favorites.
    """
    # Check if salon exists
    salon = db.query(Salon).filter(Salon.id == salon_id).first()
    if not salon:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Salon not found"
        )
    
    # Check if already favorited
    existing = db.query(CustomerFavoriteSalon).filter(
        CustomerFavoriteSalon.customer_id == current_customer.id,
        CustomerFavoriteSalon.salon_id == salon_id
    ).first()
    
    if existing:
        return {"message": "Salon already in favorites", "is_favorite": True}
    
    # Add to favorites
    favorite = CustomerFavoriteSalon(
        customer_id=current_customer.id,
        salon_id=salon_id
    )
    db.add(favorite)
    db.commit()
    
    return {"message": "Salon added to favorites", "is_favorite": True}


@router.delete("/{salon_id}")
async def remove_favorite(
    salon_id: int,
    db: Session = Depends(get_db),
    current_customer: Customer = Depends(get_current_customer)
):
    """
    Remove a salon from favorites.
    """
    favorite = db.query(CustomerFavoriteSalon).filter(
        CustomerFavoriteSalon.customer_id == current_customer.id,
        CustomerFavoriteSalon.salon_id == salon_id
    ).first()
    
    if not favorite:
        return {"message": "Salon not in favorites", "is_favorite": False}
    
    db.delete(favorite)
    db.commit()
    
    return {"message": "Salon removed from favorites", "is_favorite": False}


@router.get("/check/{salon_id}")
async def check_favorite(
    salon_id: int,
    db: Session = Depends(get_db),
    current_customer: Customer = Depends(get_current_customer)
):
    """
    Check if a specific salon is favorited.
    """
    favorite = db.query(CustomerFavoriteSalon).filter(
        CustomerFavoriteSalon.customer_id == current_customer.id,
        CustomerFavoriteSalon.salon_id == salon_id
    ).first()
    
    return {"is_favorite": favorite is not None}
