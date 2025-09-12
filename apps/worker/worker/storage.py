# apps/worker/worker/storage.py
import os
import logging
from typing import Tuple, Optional

logger = logging.getLogger(__name__)


def save_local(path: str, dest_dir: Optional[str] = None) -> str:
    """
    Move or copy file to dest_dir. If dest_dir not set, leave in current dir.
    Returns final path.
    """
    if not dest_dir:
        return os.path.abspath(path)
    os.makedirs(dest_dir, exist_ok=True)
    basename = os.path.basename(path)
    dest = os.path.join(dest_dir, basename)
    # simple copy
    with open(path, "rb") as fr, open(dest, "wb") as fw:
        fw.write(fr.read())
    return os.path.abspath(dest)


def maybe_upload_s3(local_path: str) -> Optional[str]:
    """
    If AWS env vars are present, upload to S3 and return public URL.
    Requires: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_S3_BUCKET, AWS_REGION (optional)
    """
    try:
        import boto3
    except Exception:
        logger.info("boto3 not installed; skipping S3 upload")
        return None

    bucket = os.environ.get("AWS_S3_BUCKET")
    if not bucket:
        logger.info("AWS_S3_BUCKET not set; skipping S3 upload")
        return None

    s3_client = boto3.client(
        "s3",
        aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
        region_name=os.environ.get("AWS_REGION"),
    )

    key = os.path.basename(local_path)
    extra_args = {"ACL": "private"}
    s3_client.upload_file(local_path, bucket, key, ExtraArgs=extra_args)

    # Construct URL (private); if you need public, adjust ACL or use presigned URLs
    region = os.environ.get("AWS_REGION", "us-east-1")
    url = f"https://{bucket}.s3.{region}.amazonaws.com/{key}"
    return url
