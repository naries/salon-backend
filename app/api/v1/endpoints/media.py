"""
Media upload endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional
from datetime import datetime
import math
from io import BytesIO

from app.core.database import get_db
from app.core.security import get_current_admin_user
from app.models.models import User, MediaUpload
from app.schemas.schemas import (
    MediaUploadResponse, 
    MediaUploadListResponse,
    MediaUploadBatchResponse
)

router = APIRouter()


@router.post("/upload", response_model=MediaUploadBatchResponse)
async def upload_media_files(
    request: Request,
    files: List[UploadFile] = File(...),
    folder: str = "uploads",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Upload multiple files directly to Cloudinary.
    
    - **files**: Multiple files to upload
    - **folder**: Folder/category for organizing files (default: "uploads")
    
    Returns immediately with completed uploads and URLs.
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")
    
    # Validate file sizes
    max_size = 50 * 1024 * 1024  # 50MB per file
    for file in files:
        file.file.seek(0, 2)  # Seek to end
        file_size = file.file.tell()
        file.file.seek(0)  # Reset to beginning
        
        if file_size > max_size:
            raise HTTPException(
                status_code=400,
                detail=f"File {file.filename} exceeds maximum size of 50MB"
            )
    
    upload_records = []
    
    for file in files:
        # Read file content
        file_content = await file.read()
        file_size = len(file_content)
        
        # Create database record with processing status
        upload = MediaUpload(
            original_filename=file.filename,
            file_type=file.content_type or "application/octet-stream",
            file_size=file_size,
            status="processing",
            folder=folder,
            salon_id=current_user.salon_id,
            uploaded_by=current_user.id,
            processing_started_at=datetime.utcnow()
        )
        
        db.add(upload)
        db.flush()  # Get the ID
        
        try:
            # Upload to Cloudinary immediately
            from app.core.storage import upload_file_to_cloudinary
            
            file_stream = BytesIO(file_content)
            result = upload_file_to_cloudinary(
                file_data=file_stream,
                filename=file.filename,
                folder=folder,
                salon_id=current_user.salon_id,
                resource_type="auto"
            )
            
            if not result:
                raise Exception("Failed to upload to Cloudinary")
            
            # Update record with success
            upload.status = "completed"
            upload.gcs_path = result.get("public_id")
            upload.public_url = result.get("secure_url")
            upload.bucket_name = "cloudinary"
            upload.completed_at = datetime.utcnow()
            upload.error_message = None
            
        except Exception as e:
            # Update record with failure
            upload.status = "failed"
            upload.error_message = str(e)
            upload.completed_at = datetime.utcnow()
        
        upload_records.append(upload)
    
    db.commit()
    
    # Refresh all records to get complete data
    for upload in upload_records:
        db.refresh(upload)
    
    successful = sum(1 for u in upload_records if u.status == "completed")
    failed = len(upload_records) - successful
    
    message = f"Uploaded {successful} file(s) successfully"
    if failed > 0:
        message += f", {failed} failed"
    
    return MediaUploadBatchResponse(
        uploads=[MediaUploadResponse.model_validate(u) for u in upload_records],
        total_files=len(upload_records),
        message=message
    )


@router.get("/uploads", response_model=MediaUploadListResponse)
def get_media_uploads(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None, description="Filter by status: pending, processing, completed, failed"),
    folder: Optional[str] = Query(None, description="Filter by folder"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Get list of media uploads with pagination and filtering.
    
    - **page**: Page number (default: 1)
    - **per_page**: Items per page (default: 20, max: 100)
    - **status**: Filter by upload status
    - **folder**: Filter by folder
    """
    query = db.query(MediaUpload)
    
    # Filter by salon for non-superadmin users
    if current_user.is_superadmin != 1:
        query = query.filter(MediaUpload.salon_id == current_user.salon_id)
    
    # Apply filters
    if status:
        query = query.filter(MediaUpload.status == status)
    
    if folder:
        query = query.filter(MediaUpload.folder == folder)
    
    # Get total count
    total = query.count()
    
    # Calculate pagination
    total_pages = math.ceil(total / per_page)
    offset = (page - 1) * per_page
    
    # Get paginated results
    uploads = query.order_by(desc(MediaUpload.created_at)).offset(offset).limit(per_page).all()
    
    return MediaUploadListResponse(
        uploads=[MediaUploadResponse.model_validate(u) for u in uploads],
        total=total,
        page=page,
        per_page=per_page,
        total_pages=total_pages
    )


@router.get("/uploads/{upload_id}", response_model=MediaUploadResponse)
def get_media_upload(
    upload_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Get details of a specific media upload by ID.
    
    - **upload_id**: ID of the media upload
    """
    query = db.query(MediaUpload).filter(MediaUpload.id == upload_id)
    
    # Filter by salon for non-superadmin users
    if current_user.is_superadmin != 1:
        query = query.filter(MediaUpload.salon_id == current_user.salon_id)
    
    upload = query.first()
    
    if not upload:
        raise HTTPException(status_code=404, detail="Media upload not found")
    
    return MediaUploadResponse.model_validate(upload)


@router.delete("/uploads/{upload_id}")
def delete_media_upload(
    upload_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Delete a media upload record.
    Note: This only deletes the database record, not the GCS file.
    
    - **upload_id**: ID of the media upload to delete
    """
    query = db.query(MediaUpload).filter(MediaUpload.id == upload_id)
    
    # Filter by salon for non-superadmin users
    if current_user.is_superadmin != 1:
        query = query.filter(MediaUpload.salon_id == current_user.salon_id)
    
    upload = query.first()
    
    if not upload:
        raise HTTPException(status_code=404, detail="Media upload not found")
    
    db.delete(upload)
    db.commit()
    
    return {"message": "Media upload deleted successfully"}


@router.delete("/uploads/{upload_id}/retry")
async def retry_media_upload(
    upload_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Mark a failed upload for deletion (retry not supported - files must be re-uploaded).
    
    - **upload_id**: ID of the failed upload
    """
    query = db.query(MediaUpload).filter(MediaUpload.id == upload_id)
    
    # Filter by salon for non-superadmin users
    if current_user.is_superadmin != 1:
        query = query.filter(MediaUpload.salon_id == current_user.salon_id)
    
    upload = query.first()
    
    if not upload:
        raise HTTPException(status_code=404, detail="Media upload not found")
    
    # Delete the failed upload record
    db.delete(upload)
    db.commit()
    
    return {
        "message": "Failed upload record deleted. Please re-upload the file using the upload endpoint.",
        "upload_id": upload_id
    }
