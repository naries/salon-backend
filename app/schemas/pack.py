from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class PackProductCreate(BaseModel):
    product_id: int
    quantity: int = Field(ge=1, description="Quantity must be at least 1")


class PackProductResponse(BaseModel):
    id: int
    product_id: int
    product_name: str
    product_price: int
    quantity: int
    total_price: int  # product_price * quantity
    
    class Config:
        from_attributes = True


class PackCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: Optional[str] = None
    custom_price: Optional[int] = Field(None, ge=0, description="Custom price in cents")
    discount_percentage: float = Field(default=0, ge=0, le=100)
    products: List[PackProductCreate] = Field(min_length=2, description="At least 2 products required")


class PackUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    custom_price: Optional[int] = Field(None, ge=0)
    discount_percentage: Optional[float] = Field(None, ge=0, le=100)
    products: Optional[List[PackProductCreate]] = Field(None, min_length=2)
    is_active: Optional[int] = Field(None, ge=0, le=1)


class PackResponse(BaseModel):
    id: int
    salon_id: int
    name: str
    description: Optional[str]
    custom_price: Optional[int]
    discount_percentage: float
    calculated_price: int  # Sum of all products without discount
    effective_price: int  # Final price after custom_price or discount
    is_active: int
    products: List[PackProductResponse]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class PackListResponse(BaseModel):
    id: int
    salon_id: int
    name: str
    description: Optional[str]
    effective_price: int
    discount_percentage: float
    product_count: int
    is_active: int
    created_at: datetime
    
    class Config:
        from_attributes = True
