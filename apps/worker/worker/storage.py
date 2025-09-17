# apps/worker/worker/storage.py
"""Storage operations for S3 uploads, database updates, and scheduling."""

import logging
from datetime import datetime
from typing import Optional

from .constants import (
    RUN_STATUS_COMPLETE_NO_DIFFS,
    RUN_STATUS_COMPLETE_WITH_DIFFS,
    RUN_STATUS_FAILED,
    TABLE_RUNS,
    TABLE_ARTIFACTS,
    ARTIFACT_TYPE_LLMS_TXT
)
from .database import get_supabase_client
from .s3_storage import upload_content_to_s3, create_artifact_record
from .scheduling import schedule_next_run
from .webhooks import call_webhooks_for_project

logger = logging.getLogger(__name__)


def get_latest_llms_txt_url(project_id: str) -> Optional[str]:
    """
    Get the most recent llms.txt URL from the artifacts table for a project.
    
    Args:
        project_id: The project ID
        
    Returns:
        The most recent llms.txt URL if found, None otherwise
    """
    try:
        supabase = get_supabase_client()
        
        # Query artifacts table for the most recent llms.txt artifact for this project
        result = supabase.table(TABLE_ARTIFACTS).select("metadata").eq("project_id", project_id).eq("type", ARTIFACT_TYPE_LLMS_TXT).order("created_at", desc=True).limit(1).execute()
        
        if result.data and len(result.data) > 0:
            metadata = result.data[0].get("metadata", {})
            public_url = metadata.get("public_url")
            if public_url:
                logger.info(f"Found latest llms.txt URL for project {project_id}: {public_url}")
                return public_url
            else:
                logger.warning(f"No public_url found in metadata for project {project_id}")
        else:
            logger.warning(f"No llms.txt artifacts found for project {project_id}")
            
        return None
        
    except Exception as e:
        logger.error(f"Error getting latest llms.txt URL for project {project_id}: {e}")
        return None


def maybe_upload_s3_from_memory(content: str, filename: str, run_id: str, project_id: str, 
                                changes_detected: bool = True, is_scheduled: bool = False) -> Optional[str]:
    """
    Upload content directly from memory to S3 and return public URL.
    Also updates the database with artifact information and run status.
    
    Args:
        content: The content to upload
        filename: The filename for the S3 object
        run_id: The run ID
        project_id: The project ID
        changes_detected: Whether changes were detected
        is_scheduled: Whether this is a scheduled run
        
    Returns:
        Public URL if successful, None otherwise
    """
    try:
        # Upload to S3
        public_url = upload_content_to_s3(content, filename)
        if not public_url:
            logger.error("Failed to upload content to S3")
            return None
        
        # Create artifact record
        artifact_id = create_artifact_record(project_id, run_id, filename, content, public_url)
        if not artifact_id:
            logger.error("Failed to create artifact record")
            return None
            
        # Update run status using the centralized function (this will also schedule next run)
        status = RUN_STATUS_COMPLETE_WITH_DIFFS if changes_detected else RUN_STATUS_COMPLETE_NO_DIFFS
        summary = f"Successfully generated llms.txt file. Artifact: {public_url}"
        
        # Use the centralized update_run_status function which handles scheduling
        success = update_run_status(run_id, status, project_id, is_scheduled, summary, public_url)
        if not success:
            logger.error(f"Failed to update run {run_id} status")
            
        return public_url
        
    except Exception as e:
        logger.error(f"Error in S3 upload and database update: {e}")
        return None


def update_run_status(run_id: str, status: str, project_id: str, is_scheduled: bool = False, summary: str = None, 
                     llms_txt_url: str = None) -> bool:
    """
    Update run status in the database with optional summary and conditionally schedule next run based on is_scheduled flag.
    This is the unified function that handles all run status updates and conditional scheduling.
    Optimized to minimize database operations.
    
    Args:
        run_id: The ID of the run to update
        status: The new status (e.g., "IN_PROGRESS", "COMPLETE_NO_DIFFS", "COMPLETE_WITH_DIFFS", "FAILED")
        project_id: The project ID (required for scheduling and webhook calls)
        is_scheduled: Whether this is a scheduled run (affects next run scheduling)
        summary: Optional summary message. If not provided, defaults will be used based on status.
        llms_txt_url: URL to the generated llms.txt file (required for webhook calls)
    """
    try:
        supabase = get_supabase_client()
        
        update_data = {
            "status": status,
            "updated_at": datetime.utcnow().isoformat()
        }
        
        if status in [RUN_STATUS_COMPLETE_NO_DIFFS, RUN_STATUS_COMPLETE_WITH_DIFFS]:
            update_data["finished_at"] = datetime.utcnow().isoformat()
            if summary:
                update_data["summary"] = summary
        elif status == RUN_STATUS_FAILED:
            update_data["finished_at"] = datetime.utcnow().isoformat()
            if summary:
                update_data["summary"] = f"Generation failed: {summary}"
            else:
                update_data["summary"] = "Generation failed"
        
        result = supabase.table(TABLE_RUNS).update(update_data).eq("id", run_id).execute()
        
        if result.data:
            logger.info(f"Updated run {run_id} status to {status}")
            
            # If run completed successfully, is_scheduled is True, and we have project_id, schedule the next run
            if status in [RUN_STATUS_COMPLETE_NO_DIFFS, RUN_STATUS_COMPLETE_WITH_DIFFS] and is_scheduled and project_id:
                logger.info(f"Scheduling next run for project {project_id} after successful completion of run {run_id}")
                schedule_next_run(project_id, run_id)
            elif status in [RUN_STATUS_COMPLETE_NO_DIFFS, RUN_STATUS_COMPLETE_WITH_DIFFS] and not is_scheduled:
                logger.info(f"Skipping next run scheduling for immediate job run {run_id}")
            
            # Call webhooks for completed runs
            if status in [RUN_STATUS_COMPLETE_NO_DIFFS, RUN_STATUS_COMPLETE_WITH_DIFFS] and project_id:
                # Determine the llms.txt URL to use
                webhook_url = llms_txt_url
                
                # If no URL provided, query the artifacts table for the most recent one
                if not webhook_url:
                    webhook_url = get_latest_llms_txt_url(project_id)
                
                # Call webhooks if we have a URL and one of the following conditions apply
                # 1. This is a manual run
                # 2. This is a scheduled run and diffs were detected.
                if webhook_url and ((not is_scheduled) or (status == RUN_STATUS_COMPLETE_WITH_DIFFS)):
                    logger.info(f"Calling webhooks for project {project_id} with llms.txt URL: {webhook_url}")
                    call_webhooks_for_project(project_id, run_id, webhook_url)
                else:
                    logger.warning(f"No llms.txt URL available for webhook calls for project {project_id}")
            elif status in [RUN_STATUS_COMPLETE_NO_DIFFS, RUN_STATUS_COMPLETE_WITH_DIFFS] and not project_id:
                logger.warning(f"Run {run_id} completed but no project_id available for webhook calls")
            
            return True
        else:
            logger.error(f"Failed to update run {run_id} status")
            return False
            
    except Exception as e:
        logger.error(f"Error updating run status: {e}")
        return False