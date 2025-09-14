# apps/worker/worker/storage.py
import os
import logging
from typing import Tuple, Optional
import boto3
from supabase import create_client, Client
from datetime import datetime, timedelta
import redis
import json
import uuid
logger = logging.getLogger(__name__)


def get_supabase_client() -> Client:
    """Get Supabase client using environment variables."""
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")  # Use service role key for server-side operations
    
    if not url or not key:
        raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY environment variables are required")
    
    return create_client(url, key)


def save_local(path: str, dest_dir: Optional[str] = None) -> str:
    """
    DEPRECATED: Move or copy file to dest_dir. If dest_dir not set, leave in current dir.
    Returns final path.
    
    This function is deprecated as the worker now processes files entirely in memory.
    Use maybe_upload_s3_from_memory() instead for direct S3 uploads.
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


def maybe_upload_s3_from_memory(content: str, filename: str, run_id: str, project_id: str, changes_detected: bool = True) -> Optional[str]:
    """
    Upload content directly from memory to S3 and return public URL.
    Also updates the database with artifact information and run status.
    Requires: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_S3_BUCKET, AWS_REGION (optional)
    """

    bucket = "llms-txt"
    if not bucket:
        logger.info("AWS_S3_BUCKET not set; skipping S3 upload")
        return None

    s3_client = boto3.client(
        service_name ="s3",
        endpoint_url = os.environ.get("AWS_S3_ENDPOINT"),
        aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
        region_name="us-west-1",
    )

    key = filename
    extra_args = {"ACL": "private"}
    
    # Upload content directly from memory
    s3_client.put_object(
        Bucket=bucket,
        Key=key,
        Body=content.encode('utf-8'),
        ContentType='text/plain' if filename.endswith('.txt') else 'application/json',
        **extra_args
    )

    public_url = f"{os.environ.get("AWS_PUBLIC_S3_PREFIX")}/{bucket}/{key}"
    logger.info(f"Uploaded to S3: {public_url}")
    
    # Get file size from content
    file_size = len(content.encode('utf-8'))
    
    # Update database with artifact information
    try:
        supabase = get_supabase_client()
        
        # Create artifact record
        artifact_data = {
            "project_id": project_id,
            "run_id": run_id,
            "type": "LLMS_TXT",
            "storage_path": f"s3://{bucket}/{key}",
            "file_name": key,
            "size_bytes": file_size,
            "metadata": {
                "public_url": public_url,
                "bucket": bucket,
                "key": key,
                "uploaded_at": datetime.utcnow().isoformat()
            }
        }
        
        # Insert artifact
        artifact_result = supabase.table("artifacts").insert(artifact_data).execute()
        
        if artifact_result.data:
            logger.info(f"Created artifact record: {artifact_result.data[0]['id']}")
            
            # Update run status based on whether changes were detected
            status = "COMPLETE_WITH_DIFFS" if changes_detected else "COMPLETE_NO_DIFFS"
            run_update_result = supabase.table("runs").update({
                "status": status,
                "finished_at": datetime.utcnow().isoformat(),
                "summary": f"Successfully generated llms.txt file. Artifact: {public_url}"
            }).eq("id", run_id).execute()
            
            if run_update_result.data:
                logger.info(f"Updated run {run_id} status to {status}")
            else:
                logger.error(f"Failed to update run {run_id} status")
        else:
            logger.error("Failed to create artifact record")
            
    except Exception as e:
        logger.error(f"Error updating database: {e}")
        # Don't fail the upload if database update fails
    
    return public_url

def get_redis_client():
    """Get Redis client using environment variables."""
    redis_url = os.environ.get("REDIS_URL", "rediss://default:AfdjAAIncDE0MmZlMWViNTJkNWU0MzVjOGEzOTYwOWQyOTQyNzAyYnAxNjMzMzE@hip-lobster-63331.upstash.io:6379")
    return redis.from_url(redis_url, decode_responses=True)


def calculate_next_run_time(cron_expression: str) -> Optional[datetime]:
    """
    Calculate the next run time based on cron expression.
    For now, we'll handle daily and weekly schedules.
    """
    if not cron_expression:
        return None
    
    now = datetime.utcnow()
    
    if cron_expression == "0 2 * * *":  # Daily at 2 AM
        next_run = now.replace(hour=2, minute=0, second=0, microsecond=0)
        if next_run <= now:
            next_run += timedelta(days=1)
        return next_run
    elif cron_expression == "0 2 * * 0":  # Weekly on Sunday at 2 AM
        next_run = now.replace(hour=2, minute=0, second=0, microsecond=0)
        days_until_sunday = (6 - now.weekday()) % 7
        if days_until_sunday == 0 and next_run <= now:
            days_until_sunday = 7
        next_run += timedelta(days=days_until_sunday)
        return next_run
    
    return None


def schedule_next_run(project_id: str, run_id: str) -> bool:
    """
    Schedule the next run for a project based on its cron expression.
    """
    try:
        supabase = get_supabase_client()
        redis_client = get_redis_client()
        
        # Get project config to find cron expression
        config_result = supabase.table("project_configs").select(
            "cron_expression, is_enabled, next_run_at"
        ).eq("project_id", project_id).single().execute()
        
        if not config_result.data:
            logger.warning(f"No config found for project {project_id}")
            return False
        
        config = config_result.data
        if not config.get("is_enabled") or not config.get("cron_expression"):
            logger.info(f"Project {project_id} has scheduling disabled or no cron expression")
            return False
        
        # Calculate next run time
        next_run_time = calculate_next_run_time(config["cron_expression"])
        if not next_run_time:
            logger.warning(f"Could not calculate next run time for project {project_id}")
            return False
        
        # Update project config with next run time
        update_result = supabase.table("project_configs").update({
            "last_run_at": datetime.utcnow().isoformat(),
            "next_run_at": next_run_time.isoformat()
        }).eq("project_id", project_id).execute()
        
        if not update_result.data:
            logger.error(f"Failed to update next run time for project {project_id}")
            return False
        
        # Get project details for the scheduled job
        project_result = supabase.table("projects").select("domain").eq("id", project_id).single().execute()
        if not project_result.data:
            logger.error(f"Project {project_id} not found")
            return False
        
        # Create a scheduled job in Redis
        job_id = str(uuid.uuid4())
        scheduled_job = {
            "id": job_id,
            "projectId": project_id,
            "url": project_result.data["domain"],
            "priority": "NORMAL",
            "render_mode": "STATIC",
            "scheduledAt": int(next_run_time.timestamp() * 1000),  # Convert to milliseconds
            "metadata": {
                "scheduled_run": True,
                "cron_expression": config["cron_expression"]
            }
        }
        
        # Add to Redis sorted set
        redis_client.zadd("scheduled:jobs", {json.dumps(scheduled_job): next_run_time.timestamp()})
        
        logger.info(f"Scheduled next run for project {project_id} at {next_run_time.isoformat()}")
        return True
        
    except Exception as e:
        logger.error(f"Error scheduling next run for project {project_id}: {e}")
        return False


def update_run_status(run_id: str, status: str, error_message: str = None) -> bool:
    """
    Update run status in the database and schedule next run if completed successfully.
    """
    try:
        supabase = get_supabase_client()
        
        update_data = {
            "status": status,
            "updated_at": datetime.utcnow().isoformat()
        }
        
        if status in ["COMPLETE_NO_DIFFS", "COMPLETE_WITH_DIFFS"]:
            update_data["finished_at"] = datetime.utcnow().isoformat()
        elif status == "FAILED":
            update_data["finished_at"] = datetime.utcnow().isoformat()
            if error_message:
                update_data["summary"] = f"Generation failed: {error_message}"
        
        result = supabase.table("runs").update(update_data).eq("id", run_id).execute()
        
        if result.data:
            logger.info(f"Updated run {run_id} status to {status}")
            
            # If run completed successfully, schedule the next run
            if status in ["COMPLETE_NO_DIFFS", "COMPLETE_WITH_DIFFS"]:
                # Get project_id from the run
                run_data = supabase.table("runs").select("project_id").eq("id", run_id).single().execute()
                if run_data.data:
                    schedule_next_run(run_data.data["project_id"], run_id)
            
            return True
        else:
            logger.error(f"Failed to update run {run_id} status")
            return False
            
    except Exception as e:
        logger.error(f"Error updating run status: {e}")
        return False
