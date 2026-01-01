from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
import uuid
from pydantic import BaseModel
from app.core.database import get_db
from app.core.security import get_current_admin_user, get_current_customer
from app.core.storage import (
    delete_file_from_gcs,
    get_file_url,
    validate_url
)
from app.models.models import CloudFile, Salon, User, Customer, MediaUpload
from app.schemas.schemas import (
    CloudFileResponse,
    LogoUploadResponse,
    LogoIconUpdate,
    LogoUrlUpdate,
    FileUrlUpload
)

router = APIRouter()

# Allowed image types for customer uploads
ALLOWED_IMAGE_TYPES = ["image/jpeg", "image/jpg", "image/png", "image/gif", "image/webp"]
MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB

# Predefined beauty-related icons (Lucide React icon names)
BEAUTY_ICONS = [
    "scissors",      # Hair cutting
    "sparkles",      # Beauty/Glamour
    "heart",         # Love/Beauty
    "flower",        # Spa/Nature
    "star",          # Premium/Excellence
    "zap",           # Energy/Quick
    "crown",         # Royal/Premium
    "feather",       # Light/Elegant
    "smile",         # Happy/Satisfaction
    "palette"        # Makeup/Artistry
]


# Schema for signed URL request
class SignedUrlRequest(BaseModel):
    filename: str
    content_type: str
    folder: str = "uploads"


@router.post("/get-upload-url")
def get_upload_signed_url(
    request: SignedUrlRequest,
    current_user: User = Depends(get_current_admin_user)
):
    """
    DEPRECATED: Use /media/upload endpoint instead for direct uploads
    
    This endpoint is maintained for backward compatibility but recommends
    using the new media upload system which works better with Cloudinary.
    """
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail="This endpoint is deprecated. Please use POST /api/v1/media/upload instead"
    )


@router.post("/upload")
def upload_file_url(
    file_data: FileUrlUpload,
    db: Session = Depends(get_db),
    current_customer: Customer = Depends(get_current_customer)
):
    """Save file URL (for customers - used in special requests)
    
    Frontend should upload file directly to GCS and send the public URL here.
    """
    # Validate URL format
    if not validate_url(file_data.file_url):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file URL"
        )
    
    # Validate file type
    if file_data.file_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed types: {', '.join(ALLOWED_IMAGE_TYPES)}"
        )
    
    # Validate file size if provided
    if file_data.file_size and file_data.file_size > MAX_IMAGE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size: {MAX_IMAGE_SIZE // (1024*1024)}MB"
        )
    
    # Save file record to database
    db_file = CloudFile(
        filename=file_data.filename,
        file_path=file_data.file_url,  # Store the full URL as file_path
        file_type=file_data.file_type,
        file_size=file_data.file_size or 0,
        uploaded_by=current_customer.id
    )
    db.add(db_file)
    db.commit()
    db.refresh(db_file)
    
    return {
        "id": db_file.id,
        "filename": db_file.filename,
        "file_url": file_data.file_url,
        "message": "File URL saved successfully"
    }


@router.get("/beauty-icons")
def get_beauty_icons():
    """Get list of predefined beauty icons"""
    return {"icons": BEAUTY_ICONS}


@router.post("/upload-logo", response_model=LogoUploadResponse)
def upload_logo_url(
    logo_data: LogoUrlUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Save logo using media ID or URL
    
    Preferred: Upload to /media/upload first, then pass media_id here.
    Legacy: Pass logo_url directly.
    """
    if not current_user.salon_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No salon associated with this user"
        )
    
    db_file = None
    
    # Handle media_id (new preferred method)
    if logo_data.media_id:
        from app.models.models import MediaUpload
        
        # Fetch MediaUpload record
        media_upload = db.query(MediaUpload).filter(
            MediaUpload.id == logo_data.media_id,
            MediaUpload.status == "completed"
        ).first()
        
        if not media_upload:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Media upload not found or not completed"
            )
        
        # Create CloudFile from media upload
        db_file = CloudFile(
            filename=media_upload.original_filename,
            file_path=media_upload.public_url or media_upload.gcs_path,
            file_type=media_upload.file_type,
            file_size=media_upload.file_size,
            uploaded_by=current_user.id
        )
    
    # Handle logo_url (legacy method)
    elif logo_data.logo_url:
        # Validate URL format
        if not validate_url(logo_data.logo_url):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid logo URL"
            )
        
        # Validate file size if provided
        max_logo_size = 5 * 1024 * 1024  # 5MB
        if logo_data.file_size and logo_data.file_size > max_logo_size:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File too large. Maximum size: {max_logo_size // (1024*1024)}MB"
            )
        
        # Save file record to database
        db_file = CloudFile(
            filename=logo_data.filename or "logo.png",
            file_path=logo_data.logo_url,
            file_type="image/png",
            file_size=logo_data.file_size or 0,
            uploaded_by=current_user.id
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either media_id or logo_url must be provided"
        )
    
    db.add(db_file)
    db.flush()
    
    # Update salon logo
    salon = db.query(Salon).filter(Salon.id == current_user.salon_id).first()
    if salon:
        # Delete old logo file record if exists
        if salon.logo_file_id:
            old_file = db.query(CloudFile).filter(CloudFile.id == salon.logo_file_id).first()
            if old_file:
                db.delete(old_file)
        
        salon.logo_type = "upload"
        salon.logo_file_id = db_file.id
        salon.logo_icon_name = None
    
    db.commit()
    db.refresh(db_file)
    
    return LogoUploadResponse(
        success=True,
        message="Logo URL saved successfully",
        file_id=db_file.id,
        file_url=logo_data.logo_url
    )


@router.put("/logo-icon", response_model=LogoUploadResponse)
def update_logo_icon(
    logo_update: LogoIconUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Update salon logo to use a predefined icon, or update default icon for superadmin"""
    
    # Validate icon name
    if logo_update.logo_icon_name not in BEAUTY_ICONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid icon name. Must be one of: {', '.join(BEAUTY_ICONS)}"
        )
    
    # If superadmin, update the default icon setting
    if current_user.is_superadmin:
        from app.models.models import SuperadminSettings
        settings = db.query(SuperadminSettings).first()
        if not settings:
            settings = SuperadminSettings(default_logo_icon=logo_update.logo_icon_name)
            db.add(settings)
        else:
            settings.default_logo_icon = logo_update.logo_icon_name
        db.commit()
        return LogoUploadResponse(
            success=True,
            message=f"Default logo icon updated to {logo_update.logo_icon_name} for new salons"
        )
    
    # For regular salon admins
    if not current_user.salon_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No salon associated with this user"
        )
    
    salon = db.query(Salon).filter(Salon.id == current_user.salon_id).first()
    if not salon:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Salon not found"
        )
    
    # Delete uploaded logo file if exists
    if salon.logo_file_id:
        old_file = db.query(CloudFile).filter(CloudFile.id == salon.logo_file_id).first()
        if old_file:
            delete_file_from_gcs(old_file.file_path)
            db.delete(old_file)
    
    # Update salon to use icon
    salon.logo_type = "icon"
    salon.logo_icon_name = logo_update.logo_icon_name
    salon.logo_file_id = None
    
    db.commit()
    
    return LogoUploadResponse(
        success=True,
        message=f"Logo updated to use {logo_update.logo_icon_name} icon"
    )


@router.get("/files/{file_id}", response_model=CloudFileResponse)
def get_file(
    file_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Get file details by ID"""
    file = db.query(CloudFile).filter(CloudFile.id == file_id).first()
    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    
    return file


@router.delete("/files/{file_id}")
def delete_file(
    file_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Delete a file"""
    file = db.query(CloudFile).filter(CloudFile.id == file_id).first()
    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    
    # Verify user owns the file or is admin of the salon
    if file.uploaded_by != current_user.id and current_user.salon_id:
        salon = db.query(Salon).filter(Salon.id == current_user.salon_id).first()
        if not salon or salon.logo_file_id != file_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to delete this file"
            )
    
    # Delete from GCS
    delete_file_from_gcs(file.file_path)
    
    # Delete from database
    db.delete(file)
    db.commit()
    
    return {"message": "File deleted successfully"}
