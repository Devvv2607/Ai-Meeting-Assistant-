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

logger = logging.getLogger(__name__)


class S3Service:
    """Service for AWS S3 operations"""

    def __init__(self):
        if not BOTO3_AVAILABLE:
            logger.warning("boto3 not available, S3 operations will not work")
            self.client = None
            self.bucket_name = settings.S3_BUCKET_NAME
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
        """Upload file to S3"""
        if not BOTO3_AVAILABLE or not self.client:
            logger.warning("S3 operations not available")
            return None

        if object_name is None:
            object_name = file_path.split("/")[-1]

        try:
            self.client.upload_file(file_path, self.bucket_name, object_name)
            logger.info(f"Uploaded {file_path} to S3 as {object_name}")
            return f"s3://{self.bucket_name}/{object_name}"
        except ClientError as e:
            logger.error(f"Error uploading file to S3: {e}")
            return None

    def download_file(self, object_name: str, file_path: str) -> bool:
        """Download file from S3"""
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
        """Generate presigned URL for S3 object"""
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
        """Delete file from S3"""
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
        """List files in S3 bucket"""
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
