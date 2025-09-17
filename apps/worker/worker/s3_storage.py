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
    DEFAULT_CONTENT_TYPE,
    ARTIFACT_TYPE_LLMS_TXT,
    TABLE_ARTIFACTS
)
from .database import get_supabase_client

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
    
    logger.debug('SUPABASE_PROJECT_ID = %s', os.environ.get(ENV_SUPABASE_PROJECT_ID))
    logger.debug('AWS_ACCESS_KEY_ID = %s', os.environ.get(ENV_AWS_ACCESS_KEY_ID))
    logger.debug('AWS_SECRET_ACCESS_KEY = %s', os.environ.get(ENV_AWS_SECRET_ACCESS_KEY))

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


def create_artifact_record(project_id: str, run_id: str, filename: str, 
                          content: str, public_url: str) -> Optional[str]:
    """
    Create an artifact record in the database.
    
    Args:
        project_id: The project ID
        run_id: The run ID
        filename: The filename
        content: The content (used to calculate file size)
        public_url: The public URL of the uploaded file
        
    Returns:
        Artifact ID if successful, None otherwise
    """
    try:
        supabase = get_supabase_client()
        
        # Get file size from content
        file_size = len(content.encode('utf-8'))
        
        # Create artifact record
        artifact_data = {
            "project_id": project_id,
            "run_id": run_id,
            "type": ARTIFACT_TYPE_LLMS_TXT,
            "storage_path": f"s3://{S3_BUCKET_NAME}/{filename}",
            "file_name": filename,
            "size_bytes": file_size,
            "metadata": {
                "public_url": public_url,
                "bucket": S3_BUCKET_NAME,
                "key": filename,
                "uploaded_at": datetime.utcnow().isoformat()
            }
        }
        
        # Insert artifact
        artifact_result = supabase.table(TABLE_ARTIFACTS).insert(artifact_data).execute()
        
        if artifact_result.data:
            artifact_id = artifact_result.data[0]['id']
            logger.info(f"Created artifact record: {artifact_id}")
            return artifact_id
        else:
            logger.error("Failed to create artifact record")
            return None
            
    except Exception as e:
        logger.error(f"Error creating artifact record: {e}")
        return None
