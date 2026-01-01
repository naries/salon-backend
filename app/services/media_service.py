"""
Media upload utilities (deprecated - uploads are now handled synchronously in endpoints)
This file is kept for reference but is no longer actively used.
"""
import os
from io import BytesIO
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.models import MediaUpload
from app.core.storage import upload_file_to_cloudinary


def process_media_upload(
    upload_id: int,
    file_content: bytes,
    db: Session
):
    """
    Background task to upload file to Cloudinary and update database record.
    
    Args:
        upload_id: ID of the MediaUpload record
        file_content: Raw bytes of the file
        db: Database session
    """
    upload = db.query(MediaUpload).filter(MediaUpload.id == upload_id).first()
    if not upload:
        return
    
    try:
        # Update status to processing
        upload.status = "processing"
        upload.processing_started_at = datetime.utcnow()
        db.commit()
        
        # Convert bytes to BytesIO for Cloudinary upload
        file_stream = BytesIO(file_content)
        
        # Upload to Cloudinary
        result = upload_file_to_cloudinary(
            file_data=file_stream,
            filename=upload.original_filename,
            folder=upload.folder,
            salon_id=upload.salon_id,
            resource_type="auto"
        )
        
        if not result:
            raise Exception("Failed to upload to Cloudinary")
        
        # Update record with success
        upload.status = "completed"
        upload.gcs_path = result.get("public_id")  # Store public_id as gcs_path for compatibility
        upload.public_url = result.get("secure_url")
        upload.bucket_name = "cloudinary"  # Identifier for storage type
        upload.completed_at = datetime.utcnow()
        upload.error_message = None
        
        db.commit()
        
    except Exception as e:
        # Update record with failure
        upload.status = "failed"
        upload.error_message = str(e)
        upload.completed_at = datetime.utcnow()
        db.commit()
        raise


async def process_multiple_uploads(
    upload_data: list,
    db: Session
):
    """
    Process multiple file uploads in background.
    
    Args:
        upload_data: List of tuples (upload_id, file_content)
        db: Database session
    """
    for upload_id, file_content in upload_data:
        try:
            process_media_upload(upload_id, file_content, db)
        except Exception as e:
            print(f"Error processing upload {upload_id}: {str(e)}")
            continue
