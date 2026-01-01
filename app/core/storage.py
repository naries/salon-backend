"""
Cloud Storage utility functions using Cloudinary
"""
import os
import re
import cloudinary
import cloudinary.uploader
import cloudinary.api
from typing import Optional, BinaryIO
from io import BytesIO
from .config import settings

# Configure Cloudinary
cloudinary.config(
    cloud_name=settings.CLOUDINARY_CLOUD_NAME,
    api_key=settings.CLOUDINARY_API_KEY,
    api_secret=settings.CLOUDINARY_API_SECRET,
    secure=True
)

# Allowed file types for logo uploads
ALLOWED_LOGO_TYPES = ["image/jpeg", "image/jpg", "image/png"]
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB


def validate_url(url: str) -> bool:
    """
    Validate URL format and ensure it's a valid HTTP/HTTPS URL
    
    Args:
        url: URL string to validate
        
    Returns:
        True if valid URL, False otherwise
    """
    if not url or not isinstance(url, str):
        return False
    
    # Basic URL validation regex
    url_pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    
    return url_pattern.match(url) is not None


def upload_file_to_cloudinary(
    file_data: BinaryIO,
    filename: str,
    folder: str = "logos",
    salon_id: Optional[int] = None,
    resource_type: str = "auto"
) -> Optional[dict]:
    """
    Upload a file to Cloudinary
    
    Args:
        file_data: Binary file data
        filename: Original filename
        folder: Folder path in Cloudinary (default: "logos")
        salon_id: Optional salon ID for organizing uploads
        resource_type: Type of resource (image, raw, video, auto)
        
    Returns:
        dict with public_id, public_url, secure_url, and resource_type if successful, None otherwise
    """
    try:
        # Build folder path with salon_id if provided
        if salon_id:
            upload_folder = f"salon_{salon_id}/{folder}"
        else:
            upload_folder = folder
        
        # Ensure file_data is at the beginning
        file_data.seek(0)
        
        # Upload to Cloudinary
        result = cloudinary.uploader.upload(
            file_data,
            folder=upload_folder,
            resource_type=resource_type,
            use_filename=True,
            unique_filename=True,
            overwrite=False
        )
        
        return {
            "public_id": result.get("public_id"),
            "public_url": result.get("url"),
            "secure_url": result.get("secure_url"),
            "resource_type": result.get("resource_type"),
            "format": result.get("format"),
            "file_path": result.get("public_id")  # For backward compatibility
        }
    except Exception as e:
        import traceback
        print(f"Error uploading file to Cloudinary: {e}")
        print(f"Full traceback: {traceback.format_exc()}")
        print(f"Cloudinary config - Cloud name: {settings.CLOUDINARY_CLOUD_NAME}, API Key: {settings.CLOUDINARY_API_KEY[:4]}...")
        return None


# Alias for backward compatibility
upload_file_to_gcs = upload_file_to_cloudinary


def delete_file_from_cloudinary(public_id: str, resource_type: str = "image") -> bool:
    """
    Delete a file from Cloudinary
    
    Args:
        public_id: Public ID of the resource in Cloudinary
        resource_type: Type of resource (image, raw, video)
        
    Returns:
        True if successful, False otherwise
    """
    try:
        result = cloudinary.uploader.destroy(public_id, resource_type=resource_type)
        return result.get("result") == "ok"
    except Exception as e:
        print(f"Error deleting file from Cloudinary: {e}")
        return False


# Alias for backward compatibility
delete_file_from_gcs = delete_file_from_cloudinary
# Alias for backward compatibility
delete_file_from_gcs = delete_file_from_cloudinary


def get_file_url(file_path_or_public_id: str) -> Optional[str]:
    """
    Get public URL for a file from Cloudinary
    
    Args:
        file_path_or_public_id: Public ID or file path of the resource
        
    Returns:
        Public URL if successful, None otherwise
    """
    try:
        # If it's already a full URL, return it
        if file_path_or_public_id.startswith(('http://', 'https://')):
            return file_path_or_public_id
        
        # Build Cloudinary URL
        url = cloudinary.CloudinaryImage(file_path_or_public_id).build_url()
        return url
    except Exception as e:
        print(f"Error getting file URL: {e}")
        return None


def validate_logo_file(content_type: str, file_size: int) -> tuple[bool, Optional[str]]:
    """
    Validate logo file type and size
    
    Args:
        content_type: MIME type of the file
        file_size: Size of the file in bytes
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if content_type not in ALLOWED_LOGO_TYPES:
        return False, f"Invalid file type. Allowed types: {', '.join(ALLOWED_LOGO_TYPES)}"
    
    if file_size > MAX_FILE_SIZE:
        return False, f"File size exceeds maximum allowed size of {MAX_FILE_SIZE / (1024 * 1024)}MB"
    
    return True, None

