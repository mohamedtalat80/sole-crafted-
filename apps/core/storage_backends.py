"""
Custom Supabase storage backend for Django
Optimized version with streaming uploads, connection pooling, and retry logic
"""
import logging
import os
import mimetypes
from urllib.parse import urljoin
from django.core.files.storage import Storage
from django.core.files.base import ContentFile
from django.utils.deconstruct import deconstructible
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from io import BytesIO

logger = logging.getLogger(__name__)

# Extensions supported by Supabase Image Transformation (render/image endpoint)
_IMAGE_EXTENSIONS = frozenset({'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp', '.avif'})


@deconstructible
class SupabaseStorage(Storage):
    """
    Custom storage backend for Supabase Storage using REST API
    Optimized with connection pooling, streaming uploads, and retry logic
    """

    def __init__(self, **settings):
        self.supabase_url = settings.get('supabase_url') or os.environ.get('SUPABASE_URL')
        self.supabase_key = settings.get('supabase_key') or os.environ.get('SUPABASE_SERVICE_ROLE_KEY')
        self.bucket_name = settings.get('bucket_name') or os.environ.get('SUPABASE_S3_BUCKET_NAME', 'media')
        self.public = settings.get('public', False)  # Private by default

        if not self.supabase_url:
            raise ValueError("SUPABASE_URL is required")
        if not self.supabase_key:
            raise ValueError("SUPABASE_SERVICE_ROLE_KEY is required")

        # Base URLs for storage API
        self.storage_url = f"{self.supabase_url}/storage/v1"
        self.object_url = f"{self.storage_url}/object"

        # Headers for authentication
        self.headers = {
            'Authorization': f'Bearer {self.supabase_key}',
            'apikey': self.supabase_key,
        }

        # Create persistent session with connection pooling
        self.session = self._create_session()

    def _create_session(self):
        """
        Create a requests session with connection pooling and retry logic
        """
        session = requests.Session()

        # Configure retry strategy
        retry_strategy = Retry(
            total=3,  # Total number of retries
            backoff_factor=1,  # Wait 1, 2, 4 seconds between retries
            status_forcelist=[408, 429, 500, 502, 503, 504],  # Retry on these HTTP status codes
            allowed_methods=["HEAD", "GET", "PUT", "POST", "DELETE", "OPTIONS", "TRACE"]
        )

        # Create adapter with connection pooling
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=10,  # Number of connection pools
            pool_maxsize=20,  # Max connections per pool
            pool_block=False  # Don't block if pool is full
        )

        # Mount adapter for both http and https
        session.mount("https://", adapter)
        session.mount("http://", adapter)

        return session

    def _clean_name(self, name):
        """Clean and normalize file name"""
        # Convert Windows backslashes to forward slashes
        name = name.replace('\\', '/')
        # Remove leading slashes
        return name.lstrip('/')

    def _get_object_url(self, name):
        """Get the URL for an object"""
        clean_name = self._clean_name(name)
        if self.public:
            return f"{self.object_url}/public/{self.bucket_name}/{clean_name}"
        else:
            return f"{self.object_url}/{self.bucket_name}/{clean_name}"

    def _get_signed_url(self, name, expire_seconds=3600):
        """Generate a signed URL for private bucket access"""
        clean_name = self._clean_name(name)
        url = f"{self.object_url}/sign/{self.bucket_name}/{clean_name}"

        try:
            response = self.session.post(
                url,
                json={'expiresIn': expire_seconds},
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            signed_path = data.get('signedURL')
            if signed_path:
                # Ensure the path starts with /storage/v1
                if not signed_path.startswith('/storage/v1'):
                    # Some versions of the API return paths starting with /object
                    # but they must be accessed via /storage/v1/object
                    if not signed_path.startswith('/'):
                        signed_path = f"/{signed_path}"
                    signed_path = f"/storage/v1{signed_path}"
                
                return f"{self.supabase_url}{signed_path}"
        except Exception as e:
            logger.warning("Error generating signed URL: %s", e)

        return None

    def _open(self, name, mode='rb'):
        """Open a file from Supabase storage"""
        url = self._get_object_url(name)

        try:
            # Stream the response to avoid loading entire file into memory
            response = self.session.get(url, headers=self.headers, timeout=30, stream=True)
            response.raise_for_status()

            # Read content in chunks
            content = BytesIO()
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    content.write(chunk)
            content.seek(0)

            return ContentFile(content.read())
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                raise FileNotFoundError(f"File not found: {name}")
            raise

    def _save(self, name, content):
        """
        Save a file to Supabase storage with streaming upload
        Optimized to avoid loading entire file into memory
        """
        clean_name = self._clean_name(name)
        # For uploads, ALWAYS use the non-public path (even for public buckets)
        # Upload endpoint: /storage/v1/object/{bucket}/{path}
        url = f"{self.object_url}/{self.bucket_name}/{clean_name}"

        # Detect content type
        content_type, _ = mimetypes.guess_type(name)
        if not content_type:
            content_type = 'application/octet-stream'

        # Upload headers
        upload_headers = self.headers.copy()
        upload_headers['Content-Type'] = content_type
        upload_headers['x-upsert'] = 'true'  # Overwrite if exists

        # Prepare file data for streaming
        if hasattr(content, 'read'):
            # It's a file-like object, reset to beginning
            if hasattr(content, 'seek'):
                content.seek(0)
            file_data = content
        else:
            # It's bytes, wrap in BytesIO
            file_data = BytesIO(content)

        try:
            # Stream upload - don't load entire file into memory
            response = self.session.post(
                url,
                data=file_data,  # Streams directly from file object
                headers=upload_headers,
                timeout=120  # Increased timeout for large files
            )
            if response.status_code != 200:
                logger.error(f"Supabase upload failed: {response.status_code} - {response.text}")
            response.raise_for_status()
            return clean_name
        except requests.exceptions.RequestException as e:
            error_msg = f"Error uploading file to Supabase: {e}"
            if hasattr(e, 'response') and e.response is not None:
                error_msg += f" - Response: {e.response.text}"
            raise IOError(error_msg)

    def delete(self, name):
        """Delete a file from Supabase storage"""
        clean_name = self._clean_name(name)
        # For delete, ALWAYS use the non-public path (even for public buckets)
        url = f"{self.object_url}/{self.bucket_name}/{clean_name}"

        try:
            response = self.session.delete(url, headers=self.headers, timeout=10)
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code != 404:
                raise

    def exists(self, name):
        """Check if a file exists in Supabase storage"""
        clean_name = self._clean_name(name)
        # Use authenticated path for HEAD requests
        url = f"{self.object_url}/{self.bucket_name}/{clean_name}"

        try:
            response = self.session.head(url, headers=self.headers, timeout=10)
            return response.status_code == 200
        except:
            return False

    def listdir(self, path):
        """List contents of a directory"""
        clean_path = self._clean_name(path) if path else ''
        url = f"{self.object_url}/list/{self.bucket_name}"

        params = {'prefix': clean_path if clean_path else ''}

        try:
            response = self.session.post(
                url,
                json=params,
                headers=self.headers,
                timeout=10
            )
            if response.status_code != 200:
                print(f"Listdir failed: {response.status_code} - {response.text}")
            response.raise_for_status()
            data = response.json()

            directories = []
            files = []

            for item in data:
                if item.get('id'):  # It's a file
                    files.append(item['name'])
                else:  # It's a directory
                    directories.append(item['name'])

            return directories, files
        except Exception as e:
            logger.warning("Error listing directory: %s", e)
            return [], []

    def list_buckets(self):
        """List all buckets in the Supabase project"""
        url = f"{self.storage_url}/bucket"
        try:
            response = self.session.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error listing buckets: {e}")
            return []

    def size(self, name):
        """Get the size of a file"""
        clean_name = self._clean_name(name)
        # Use authenticated path for HEAD requests
        url = f"{self.object_url}/{self.bucket_name}/{clean_name}"

        try:
            response = self.session.head(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            return int(response.headers.get('Content-Length', 0))
        except:
            return 0

    def url(self, name):
        """Get the URL for accessing the file.

        For public buckets, image files are served via the Supabase Image
        Transformation API (quality=80) to reduce egress.
        Requires Image Transformations to be enabled in Supabase Dashboard
        (Storage → Configuration → Enable Image Transformations).
        """
        if self.public:
            clean_name = self._clean_name(name)
            ext = os.path.splitext(clean_name)[1].lower()
            if ext in _IMAGE_EXTENSIONS:
                return (
                    f"{self.storage_url}/render/image/public"
                    f"/{self.bucket_name}/{clean_name}"
                    f"?quality=80"
                )
            return f"{self.object_url}/public/{self.bucket_name}/{clean_name}"
        else:
            # For private buckets, return signed URL
            signed_url = self._get_signed_url(name, expire_seconds=3600)
            if signed_url:
                return signed_url
            # Fallback to object URL (will require auth)
            return self._get_object_url(name)

    def get_accessed_time(self, name):
        """Not supported by Supabase Storage API"""
        raise NotImplementedError("Supabase Storage does not provide access time.")

    def get_created_time(self, name):
        """Get created time from Supabase metadata"""
        # Would require additional API call to get metadata
        raise NotImplementedError("Created time requires additional API implementation.")

    def get_modified_time(self, name):
        """Get modified time from Supabase metadata"""
        # Would require additional API call to get metadata
        raise NotImplementedError("Modified time requires additional API implementation.")

    def __del__(self):
        """Close session when storage instance is destroyed"""
        if hasattr(self, 'session'):
            self.session.close()
