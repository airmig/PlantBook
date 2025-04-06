import os
import logging
import requests
from urllib.parse import urljoin
import mimetypes
from django.core.files.storage import Storage
from django.conf import settings

logger = logging.getLogger(__name__)

# Log when the module is loaded
logger.info("Loading storage_backends.py module")

class SupabaseStorage(Storage):
    def __init__(self, bucket_name='media'):
        logger.info("Initializing SupabaseStorage")
        self.bucket_name = bucket_name
        self.base_url = settings.SUPABASE_URL
        self.api_key = settings.SUPABASE_KEY
        self.headers = {
            'apikey': self.api_key,
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        logger.info(f"Supabase URL: {self.base_url}")
        logger.info(f"Bucket name: {self.bucket_name}")

    def _get_upload_url(self, name):
        """Get the upload URL for a file"""
        url = urljoin(self.base_url, f'/storage/v1/object/{self.bucket_name}/{name}')
        logger.info(f"Upload URL: {url}")
        return url

    def _get_download_url(self, name):
        """Get the download URL for a file"""
        url = urljoin(self.base_url, f'/storage/v1/object/public/{self.bucket_name}/{name}')
        logger.info(f"Download URL: {url}")
        return url

    def _save(self, name, content):
        """Save a file to Supabase Storage"""
        logger.info(f"Starting _save operation for file: {name}")
        try:
            if hasattr(content, 'seek'):
                content.seek(0)

            # Get the content type
            content_type = mimetypes.guess_type(name)[0] or 'application/octet-stream'
            logger.info(f"Content type: {content_type}")

            # Prepare the upload
            upload_url = self._get_upload_url(name)
            files = {'file': (name, content, content_type)}
            
            # Upload the file
            logger.info("Attempting to upload file to Supabase...")
            response = requests.post(
                upload_url,
                headers=self.headers,
                files=files
            )
            
            if response.status_code not in [200, 201]:
                error_msg = f"Failed to upload file: {response.text}"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            logger.info(f"File uploaded successfully: {name}")
            return name
        except Exception as e:
            logger.error(f"Error saving file to Supabase: {str(e)}", exc_info=True)
            raise

    def url(self, name):
        """Get the URL for a file"""
        if not name:
            return ''
        url = self._get_download_url(name)
        logger.info(f"Generated URL for {name}: {url}")
        return url

    def exists(self, name):
        """Check if a file exists"""
        if not name:
            return False
        url = self._get_upload_url(name)
        response = requests.head(url, headers=self.headers)
        exists = response.status_code == 200
        logger.info(f"File {name} exists: {exists}")
        return exists

    def delete(self, name):
        """Delete a file"""
        if not name:
            return False
        url = self._get_upload_url(name)
        response = requests.delete(url, headers=self.headers)
        deleted = response.status_code == 200
        logger.info(f"File {name} deleted: {deleted}")
        return deleted

    def size(self, name):
        """Get the size of a file"""
        if not name:
            return 0
        url = self._get_upload_url(name)
        response = requests.head(url, headers=self.headers)
        if response.status_code == 200:
            size = int(response.headers.get('content-length', 0))
            logger.info(f"File {name} size: {size}")
            return size
        return 0

# Log when the module is fully loaded
logger.info("storage_backends.py module loaded successfully") 