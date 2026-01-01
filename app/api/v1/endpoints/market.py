from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import List, Optional
from math import radians, cos, sin, asin, sqrt
from app.core.database import get_db
from app.models.models import Salon, Review
from pydantic import BaseModel
from datetime import datetime

router = APIRouter()


# Response schemas for market
class SalonMarketResponse(BaseModel):
    id: int
    name: str
    slug: str
    address: Optional[str] = None
    phone: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    logo_type: str
    logo_icon_name: str
    logo_file_id: Optional[int] = None
    opening_hour: int
    closing_hour: int
    about_us: Optional[str] = None
    instagram_url: Optional[str] = None
    tiktok_url: Optional[str] = None
    facebook_url: Optional[str] = None
    average_rating: float = 0.0
    total_reviews: int = 0
    distance_km: Optional[float] = None

    class Config:
        from_attributes = True


class MarketResponse(BaseModel):
    top_rated: List[SalonMarketResponse]
    nearby: List[SalonMarketResponse]
    all_salons: List[SalonMarketResponse]
    total_count: int


def haversine(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    """
    Calculate the great circle distance in kilometers between two points 
    on the earth (specified in decimal degrees)
    """
    # Convert decimal degrees to radians
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    
    # Haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    
    # Radius of earth in kilometers
    r = 6371
    
    return c * r


def get_salon_with_rating(db: Session, salon: Salon, user_lat: Optional[float] = None, user_lng: Optional[float] = None) -> dict:
    """Get salon data with rating information and optional distance"""
    # Get rating stats
    reviews = db.query(Review).filter(
        Review.salon_id == salon.id,
        Review.is_approved == 1,
        Review.is_visible == 1
    ).all()
    
    total_reviews = len(reviews)
    average_rating = round(sum(r.rating for r in reviews) / total_reviews, 1) if total_reviews > 0 else 0.0
    
    # Calculate distance if user location provided
    distance_km = None
    if user_lat is not None and user_lng is not None and salon.latitude and salon.longitude:
        distance_km = round(haversine(user_lng, user_lat, salon.longitude, salon.latitude), 2)
    
    return {
        "id": salon.id,
        "name": salon.name,
        "slug": salon.slug,
        "address": salon.address,
        "phone": salon.phone,
        "latitude": salon.latitude,
        "longitude": salon.longitude,
        "logo_type": salon.logo_type,
        "logo_icon_name": salon.logo_icon_name,
        "logo_file_id": salon.logo_file_id,
        "opening_hour": salon.opening_hour,
        "closing_hour": salon.closing_hour,
        "about_us": salon.about_us,
        "instagram_url": salon.instagram_url,
        "tiktok_url": salon.tiktok_url,
        "facebook_url": salon.facebook_url,
        "average_rating": average_rating,
        "total_reviews": total_reviews,
        "distance_km": distance_km
    }


@router.get("/", response_model=MarketResponse)
def get_market_data(
    lat: Optional[float] = Query(None, description="User's latitude"),
    lng: Optional[float] = Query(None, description="User's longitude"),
    db: Session = Depends(get_db)
):
    """
    Get market data with top-rated salons, nearby salons, and all salons.
    Public endpoint for the market page.
    """
    # Get all active salons
    salons = db.query(Salon).filter(Salon.is_active == 1).all()
    
    # Build salon data with ratings
    salon_data = [get_salon_with_rating(db, s, lat, lng) for s in salons]
    
    # Sort by rating for top rated (descending)
    top_rated = sorted(
        [s for s in salon_data if s["total_reviews"] > 0],
        key=lambda x: (x["average_rating"], x["total_reviews"]),
        reverse=True
    )[:6]  # Top 6 rated salons
    
    # Sort by distance for nearby (ascending)
    nearby = []
    if lat is not None and lng is not None:
        salons_with_location = [s for s in salon_data if s["distance_km"] is not None]
        nearby = sorted(salons_with_location, key=lambda x: x["distance_km"])[:6]  # 6 nearest
    
    return MarketResponse(
        top_rated=top_rated,
        nearby=nearby,
        all_salons=salon_data,
        total_count=len(salon_data)
    )


@router.get("/search", response_model=List[SalonMarketResponse])
def search_salons(
    q: str = Query(..., min_length=1, description="Search query"),
    lat: Optional[float] = Query(None, description="User's latitude for distance"),
    lng: Optional[float] = Query(None, description="User's longitude for distance"),
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """
    Search salons by name or address.
    Public endpoint.
    """
    search_term = f"%{q.lower()}%"
    
    salons = db.query(Salon).filter(
        Salon.is_active == 1,
        (func.lower(Salon.name).like(search_term) | func.lower(Salon.address).like(search_term))
    ).offset(skip).limit(limit).all()
    
    return [get_salon_with_rating(db, s, lat, lng) for s in salons]


@router.get("/top-rated", response_model=List[SalonMarketResponse])
def get_top_rated_salons(
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """
    Get top-rated salons sorted by rating.
    Public endpoint.
    """
    # Get all active salons
    salons = db.query(Salon).filter(Salon.is_active == 1).all()
    
    # Build salon data with ratings
    salon_data = [get_salon_with_rating(db, s) for s in salons]
    
    # Sort by rating (descending), then by review count
    sorted_salons = sorted(
        salon_data,
        key=lambda x: (x["average_rating"], x["total_reviews"]),
        reverse=True
    )
    
    return sorted_salons[skip:skip + limit]


@router.get("/nearby", response_model=List[SalonMarketResponse])
def get_nearby_salons(
    lat: float = Query(..., description="User's latitude"),
    lng: float = Query(..., description="User's longitude"),
    radius_km: float = Query(50, description="Search radius in kilometers"),
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """
    Get salons near a location, sorted by distance.
    Public endpoint.
    """
    # Get all active salons with coordinates
    salons = db.query(Salon).filter(
        Salon.is_active == 1,
        Salon.latitude.isnot(None),
        Salon.longitude.isnot(None)
    ).all()
    
    # Calculate distances and filter by radius
    salon_data = []
    for salon in salons:
        data = get_salon_with_rating(db, salon, lat, lng)
        if data["distance_km"] is not None and data["distance_km"] <= radius_km:
            salon_data.append(data)
    
    # Sort by distance (ascending)
    sorted_salons = sorted(salon_data, key=lambda x: x["distance_km"])
    
    return sorted_salons[skip:skip + limit]
