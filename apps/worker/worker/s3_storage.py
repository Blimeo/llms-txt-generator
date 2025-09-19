# apps/worker/worker/s3_storage.py
"""S3 storage operations for file uploads."""

import os
import logging
from datetime import datetime
from typing import Optional

import boto3

from .constants import (
    ENV_SUPABASE_PROJECT_ID,
    ENV_AWS_ACCESS_KEY_ID,
    ENV_AWS_SECRET_ACCESS_KEY,
    S3_BUCKET_NAME,
    S3_REGION,
    DEFAULT_CONTENT_TYPE
)

logger = logging.getLogger(__name__)


def upload_content_to_s3(content: str, filename: str) -> Optional[str]:
    """
    Upload content directly from memory to S3 and return public URL.
    
    Args:
        content: The content to upload
        filename: The filename/key for the S3 object
        
    Returns:
        Public URL if successful, None otherwise
    """
    bucket = S3_BUCKET_NAME
    if not bucket:
        logger.info("S3 bucket not configured; skipping S3 upload")
        return None

    s3_client = boto3.client(
        service_name="s3",
        endpoint_url=f"https://{os.environ.get(ENV_SUPABASE_PROJECT_ID)}.supabase.co/storage/v1/s3",
        aws_access_key_id=os.environ.get(ENV_AWS_ACCESS_KEY_ID),
        aws_secret_access_key=os.environ.get(ENV_AWS_SECRET_ACCESS_KEY),
        region_name=S3_REGION,
    )
    
    key = filename
    extra_args = {"ACL": "private"}
    
    # Upload content directly from memory
    s3_client.put_object(
        Bucket=bucket,
        Key=key,
        Body=content.encode('utf-8'),
        ContentType=DEFAULT_CONTENT_TYPE,
        **extra_args
    )

    # Construct Supabase storage URL using the project ID
    supabase_project_id = os.environ.get(ENV_SUPABASE_PROJECT_ID)
    public_url = f"https://{supabase_project_id}.supabase.co/storage/v1/object/public/{bucket}/{key}"
    logger.info(f"Uploaded to S3: {public_url}")
    
    return public_url


