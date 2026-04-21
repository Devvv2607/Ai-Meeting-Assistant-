try:
    import boto3
    from botocore.exceptions import ClientError
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False
    ClientError = None

from app.config import settings
from typing import Optional
import logging
import os
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)


class S3Service:
    """Service for AWS S3 operations with local storage fallback"""

    def __init__(self):
        # Check if AWS credentials are configured (not placeholder values)
        self.use_local_storage = (
            not settings.AWS_ACCESS_KEY_ID 
            or not settings.AWS_SECRET_ACCESS_KEY
            or settings.AWS_ACCESS_KEY_ID == "your_aws_access_key"
            or settings.AWS_SECRET_ACCESS_KEY == "your_aws_secret_key"
        )
        
        if self.use_local_storage:
            logger.info("AWS credentials not configured, using local file storage")
            self.client = None
            self.bucket_name = settings.S3_BUCKET_NAME
            # Create local storage directory
            self.local_storage_path = Path("backend/uploads")
            self.local_storage_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Local storage directory: {self.local_storage_path.absolute()}")
            return
        
        if not BOTO3_AVAILABLE:
            logger.warning("boto3 not available, falling back to local storage")
            self.use_local_storage = True
            self.client = None
            self.bucket_name = settings.S3_BUCKET_NAME
            self.local_storage_path = Path("backend/uploads")
            self.local_storage_path.mkdir(parents=True, exist_ok=True)
            return

        self.client = boto3.client(
            "s3",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION,
            endpoint_url=settings.S3_ENDPOINT_URL,
        )
        self.bucket_name = settings.S3_BUCKET_NAME

    def upload_file(
        self, file_path: str, object_name: Optional[str] = None
    ) -> Optional[str]:
        """Upload file to S3 or local storage"""
        if object_name is None:
            object_name = os.path.basename(file_path)
        
        # Use local storage if AWS not configured
        if self.use_local_storage:
            try:
                # Create destination path
                dest_path = self.local_storage_path / object_name
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Copy file to local storage
                shutil.copy2(file_path, dest_path)
                logger.info(f"Saved {file_path} to local storage as {dest_path}")
                
                # Return local file path with local:// prefix
                return f"local://{object_name}"
            except Exception as e:
                logger.error(f"Error saving file to local storage: {e}")
                return None

        # Use S3 if configured
        if not BOTO3_AVAILABLE or not self.client:
            logger.warning("S3 operations not available")
            return None

        try:
            self.client.upload_file(file_path, self.bucket_name, object_name)
            logger.info(f"Uploaded {file_path} to S3 as {object_name}")
            return f"s3://{self.bucket_name}/{object_name}"
        except ClientError as e:
            logger.error(f"Error uploading file to S3: {e}")
            return None

    def download_file(self, object_name: str, file_path: str) -> bool:
        """Download file from S3 or local storage"""
        # Use local storage if AWS not configured
        if self.use_local_storage:
            try:
                source_path = self.local_storage_path / object_name
                if not source_path.exists():
                    logger.error(f"File not found in local storage: {source_path}")
                    return False
                
                shutil.copy2(source_path, file_path)
                logger.info(f"Downloaded {object_name} from local storage to {file_path}")
                return True
            except Exception as e:
                logger.error(f"Error downloading file from local storage: {e}")
                return False
        
        # Use S3 if configured
        if not BOTO3_AVAILABLE or not self.client:
            logger.warning("S3 operations not available")
            return False

        try:
            self.client.download_file(self.bucket_name, object_name, file_path)
            logger.info(f"Downloaded {object_name} from S3 to {file_path}")
            return True
        except ClientError as e:
            logger.error(f"Error downloading file from S3: {e}")
            return False

    def generate_presigned_url(
        self, object_name: str, expiration: int = 3600
    ) -> Optional[str]:
        """Generate presigned URL for S3 object or local file path"""
        # For local storage, return the local file path
        if self.use_local_storage:
            local_path = self.local_storage_path / object_name
            if local_path.exists():
                return f"local://{object_name}"
            logger.warning(f"File not found in local storage: {local_path}")
            return None
        
        # Use S3 if configured
        if not BOTO3_AVAILABLE or not self.client:
            logger.warning("S3 operations not available")
            return None

        try:
            url = self.client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket_name, "Key": object_name},
                ExpiresIn=expiration,
            )
            return url
        except ClientError as e:
            logger.error(f"Error generating presigned URL: {e}")
            return None

    def delete_file(self, object_name: str) -> bool:
        """Delete file from S3 or local storage"""
        # Use local storage if AWS not configured
        if self.use_local_storage:
            try:
                file_path = self.local_storage_path / object_name
                if file_path.exists():
                    file_path.unlink()
                    logger.info(f"Deleted {object_name} from local storage")
                    return True
                logger.warning(f"File not found in local storage: {file_path}")
                return False
            except Exception as e:
                logger.error(f"Error deleting file from local storage: {e}")
                return False
        
        # Use S3 if configured
        if not BOTO3_AVAILABLE or not self.client:
            logger.warning("S3 operations not available")
            return False

        try:
            self.client.delete_object(Bucket=self.bucket_name, Key=object_name)
            logger.info(f"Deleted {object_name} from S3")
            return True
        except ClientError as e:
            logger.error(f"Error deleting file from S3: {e}")
            return False

    def list_files(self, prefix: str = "") -> list:
        """List files in S3 bucket or local storage"""
        # Use local storage if AWS not configured
        if self.use_local_storage:
            try:
                files = []
                search_path = self.local_storage_path / prefix if prefix else self.local_storage_path
                if search_path.exists():
                    for file in search_path.rglob("*"):
                        if file.is_file():
                            rel_path = file.relative_to(self.local_storage_path)
                            files.append(str(rel_path).replace("\\", "/"))
                return files
            except Exception as e:
                logger.error(f"Error listing local storage files: {e}")
                return []
        
        # Use S3 if configured
        try:
            response = self.client.list_objects_v2(
                Bucket=self.bucket_name, Prefix=prefix
            )
            return [obj["Key"] for obj in response.get("Contents", [])]
        except ClientError as e:
            logger.error(f"Error listing S3 files: {e}")
            return []


# Global S3 service instance
s3_service = S3Service()
