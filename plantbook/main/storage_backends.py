import os
import logging
import cloudinary
import cloudinary.uploader
from django.core.files.storage import Storage
from django.conf import settings

logger = logging.getLogger(__name__)

# Log when the module is loaded
logger.info("Loading storage_backends.py module")

class CloudinaryStorage(Storage):
    def __init__(self):
        logger.info("Initializing CloudinaryStorage")
        # Configure Cloudinary using the cloudinary_url
        cloudinary_url = os.getenv('CLOUDINARY_URL')
        if not cloudinary_url:
            raise ValueError("CLOUDINARY_URL must be set in environment variables")
        cloudinary.config(cloudinary_url=cloudinary_url)
        logger.info("Cloudinary configured successfully")

    def _save(self, name, content):
        """Save a file to Cloudinary"""
        logger.info(f"Starting _save operation for file: {name}")
        try:
            if hasattr(content, 'seek'):
                content.seek(0)

            # Upload to Cloudinary
            logger.info("Attempting to upload file to Cloudinary...")
            result = cloudinary.uploader.upload(
                content,
                resource_type="auto",
                folder="profile_photos"
            )
            
            if not result or 'secure_url' not in result:
                error_msg = "Failed to upload file to Cloudinary"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            # Log the secure URL before returning
            logger.info(f"File uploaded successfully. Secure URL: {result['secure_url']}")
            return result['secure_url']
        except Exception as e:
            logger.error(f"Error saving file to Cloudinary: {str(e)}", exc_info=True)
            raise

    def url(self, name):
        """Get the URL for a file"""
        if not name:
            return ''
        logger.info(f"Generated URL for {name}: {name}")
        return name

    def exists(self, name):
        """Check if a file exists"""
        if not name:
            return False
        try:
            result = cloudinary.api.resource(name)
            exists = result is not None
            logger.info(f"File {name} exists: {exists}")
            return exists
        except Exception:
            return False

    def delete(self, name):
        """Delete a file"""
        if not name:
            return False
        try:
            result = cloudinary.uploader.destroy(name)
            deleted = result.get('result') == 'ok'
            logger.info(f"File {name} deleted: {deleted}")
            return deleted
        except Exception:
            return False

    def size(self, name):
        """Get the size of a file"""
        if not name:
            return 0
        try:
            result = cloudinary.api.resource(name)
            size = result.get('bytes', 0)
            logger.info(f"File {name} size: {size}")
            return size
        except Exception:
            return 0

# Log when the module is fully loaded
logger.info("storage_backends.py module loaded successfully") 