# apps/worker/worker/storage.py
import os
import logging
from typing import Tuple, Optional
import boto3
from supabase import create_client, Client
from datetime import datetime, timedelta
import uuid
from .cloud_tasks_client import get_cloud_tasks_client
logger = logging.getLogger(__name__)


def enqueue_immediate_job(project_id: str, url: str, run_id: str = None) -> bool:
    """
    Enqueue an immediate job using Cloud Tasks.
    
    Args:
        project_id: The project ID
        url: The URL to crawl
        run_id: Optional run ID (will be generated if not provided)
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Generate run_id if not provided
        if not run_id:
            run_id = str(uuid.uuid4())
        
        # Create job payload for Cloud Tasks
        job_id = f"immediate_{project_id}_{run_id}"
        job_payload = {
            "id": job_id,
            "projectId": project_id,
            "runId": run_id,
            "url": url,
            "priority": "immediate",
            "render_mode": "immediate",
            "metadata": {
                "enqueued_by": "worker",
                "enqueued_at": datetime.utcnow().isoformat()
            }
        }
        
        # Enqueue the task using Cloud Tasks
        tasks_client = get_cloud_tasks_client()
        task_name = tasks_client.enqueue_immediate_job(job_payload)
        
        if not task_name:
            logger.error(f"Failed to enqueue immediate task for project {project_id}")
            return False
        
        logger.info(f"Enqueued immediate job for project {project_id} with task {task_name}")
        return True
        
    except Exception as e:
        logger.error(f"Error enqueueing immediate job for project {project_id}: {e}")
        return False


def cancel_scheduled_job(project_id: str, job_id: str) -> bool:
    """
    Cancel a scheduled job using Cloud Tasks.
    
    Args:
        project_id: The project ID
        job_id: The job ID to cancel
        
    Returns:
        True if successful, False otherwise
    """
    try:
        tasks_client = get_cloud_tasks_client()
        success = tasks_client.cancel_scheduled_job(job_id)
        
        if success:
            logger.info(f"Cancelled scheduled job {job_id} for project {project_id}")
        else:
            logger.error(f"Failed to cancel scheduled job {job_id} for project {project_id}")
        
        return success
        
    except Exception as e:
        logger.error(f"Error cancelling scheduled job {job_id} for project {project_id}: {e}")
        return False


def get_supabase_client() -> Client:
    """Get Supabase client using environment variables."""
    url = os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
    key = os.environ.get("NEXT_PUBLIC_SUPABASE_ANON_KEY") 
    
    if not url or not key:
        raise ValueError("NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY environment variables are required")
    
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
        endpoint_url = f"https://{os.environ.get('SUPABASE_PROJECT_ID')}.supabase.co/storage/v1/s3",
        aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
        region_name="us-west-1",
    )
    logger.info('SUPABASE_PROJECT_ID = %s', os.environ.get('SUPABASE_PROJECT_ID'))
    logger.info('AWS_ACCESS_KEY_ID = %s', os.environ.get("AWS_ACCESS_KEY_ID"))
    logger.info('AWS_SECRET_ACCESS_KEY = %s', os.environ.get("AWS_SECRET_ACCESS_KEY"))

    key = filename
    extra_args = {"ACL": "private"}
    
    # Upload content directly from memory
    s3_client.put_object(
        Bucket=bucket,
        Key=key,
        Body=content.encode('utf-8'),
        ContentType='text/plain',
        **extra_args
    )

    # Construct Supabase storage URL using the project ID
    supabase_project_id = os.environ.get("SUPABASE_PROJECT_ID")
    public_url = f"https://{supabase_project_id}.supabase.co/storage/v1/object/public/{bucket}/{key}"
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
            
            # Update run status using the centralized function (this will also schedule next run)
            status = "COMPLETE_WITH_DIFFS" if changes_detected else "COMPLETE_NO_DIFFS"
            summary = f"Successfully generated llms.txt file. Artifact: {public_url}"
            
            # Use the centralized update_run_status function which handles scheduling
            success = update_run_status_with_summary(run_id, status, summary)
            if not success:
                logger.error(f"Failed to update run {run_id} status")
        else:
            logger.error("Failed to create artifact record")
            
    except Exception as e:
        logger.error(f"Error updating database: {e}")
        # Don't fail the upload if database update fails
    
    return public_url

def calculate_next_run_time(cron_expression: str) -> Optional[datetime]:
    """
    Calculate the next run time based on cron expression.
    For now, we'll handle daily and weekly schedules.
    """
    if not cron_expression:
        return None
    
    now = datetime.utcnow()
    # When we support custom schedules, this will use a proper cron expression parsing library.
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
    This function now enqueues the task using Google Cloud Tasks.
    Optimized to minimize database operations by joining tables.
    """
    try:
        supabase = get_supabase_client()
        
        # Get project config and domain in a single query by joining tables
        # Note: We need to construct the URL from the domain field in projects table
        config_result = supabase.table("project_configs").select(
            "cron_expression, is_enabled, next_run_at, projects!inner(domain)"
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
        
        # Construct URL from domain (assuming https protocol)
        domain = config.get("projects", {}).get("domain", "")
        if not domain:
            logger.warning(f"No domain found for project {project_id}")
            return False
        
        # Create job payload for Cloud Tasks
        job_id = f"scheduled_{project_id}_{int(next_run_time.timestamp())}"
        job_payload = {
            "id": job_id,
            "projectId": project_id,
            "url": domain,
            "priority": "scheduled",
            "render_mode": "scheduled",
            "scheduledAt": int(next_run_time.timestamp() * 1000),  # Convert to milliseconds
            "metadata": {
                "cron_expression": config["cron_expression"],
                "scheduled_by": "worker"
            }
        }
        
        # Enqueue the task using Cloud Tasks
        tasks_client = get_cloud_tasks_client()
        task_name = tasks_client.schedule_job(job_payload, next_run_time)
        
        if not task_name:
            logger.error(f"Failed to enqueue scheduled task for project {project_id}")
            return False
        
        # Update project config with next run time and task name in a single operation
        current_time = datetime.utcnow().isoformat()
        update_result = supabase.table("project_configs").update({
            "last_run_at": current_time,
            "next_run_at": next_run_time.isoformat(),
            "scheduled_task_name": task_name
        }).eq("project_id", project_id).execute()
        
        if not update_result.data:
            logger.error(f"Failed to update next run time for project {project_id}")
            return False
        
        logger.info(f"Scheduled next run for project {project_id} at {next_run_time.isoformat()} with task {task_name}")
        return True
        
    except Exception as e:
        logger.error(f"Error scheduling next run for project {project_id}: {e}")
        return False


def update_run_status(run_id: str, status: str, error_message: str = None) -> bool:
    """
    Update run status in the database and schedule next run if completed successfully.
    """
    return update_run_status_with_summary(run_id, status, error_message)


def update_run_status_with_summary(run_id: str, status: str, summary: str = None) -> bool:
    """
    Update run status in the database with custom summary and schedule next run if completed successfully.
    This is the core function that handles all run status updates and scheduling.
    Optimized to minimize database operations.
    """
    try:
        supabase = get_supabase_client()
        
        # If we need to schedule next run, get project_id first to avoid extra query
        project_id = None
        if status in ["COMPLETE_NO_DIFFS", "COMPLETE_WITH_DIFFS"]:
            run_data = supabase.table("runs").select("project_id").eq("id", run_id).single().execute()
            if run_data.data:
                project_id = run_data.data["project_id"]
            else:
                logger.warning(f"Could not find project_id for run {run_id}")
        
        update_data = {
            "status": status,
            "updated_at": datetime.utcnow().isoformat()
        }
        
        if status in ["COMPLETE_NO_DIFFS", "COMPLETE_WITH_DIFFS"]:
            update_data["finished_at"] = datetime.utcnow().isoformat()
            if summary:
                update_data["summary"] = summary
        elif status == "FAILED":
            update_data["finished_at"] = datetime.utcnow().isoformat()
            if summary:
                update_data["summary"] = f"Generation failed: {summary}"
            elif not summary:  # Backward compatibility
                update_data["summary"] = "Generation failed"
        
        result = supabase.table("runs").update(update_data).eq("id", run_id).execute()
        
        if result.data:
            logger.info(f"Updated run {run_id} status to {status}")
            
            # If run completed successfully and we have project_id, schedule the next run
            if status in ["COMPLETE_NO_DIFFS", "COMPLETE_WITH_DIFFS"] and project_id:
                logger.info(f"Scheduling next run for project {project_id} after successful completion of run {run_id}")
                schedule_next_run(project_id, run_id)
            
            return True
        else:
            logger.error(f"Failed to update run {run_id} status")
            return False
            
    except Exception as e:
        logger.error(f"Error updating run status: {e}")
        return False
