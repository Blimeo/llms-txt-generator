# apps/worker/worker/scheduling.py
"""Scheduling and cron expression handling."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from .constants import (
    CRON_DAILY_2AM,
    CRON_WEEKLY_SUNDAY_2AM
)
from .data_fetcher import DataFetcher
from .cloud_tasks_client import get_cloud_tasks_client

logger = logging.getLogger(__name__)


def calculate_next_run_time(cron_expression: str) -> Optional[datetime]:
    """
    Calculate the next run time based on cron expression.
    For now, we'll handle daily and weekly schedules.
    """
    if not cron_expression:
        return None
    
    now = datetime.now(timezone.utc)
    # When we support custom schedules, this will use a proper cron expression parsing library.
    if cron_expression == CRON_DAILY_2AM:  # Daily at 2 AM
        next_run = now.replace(hour=2, minute=0, second=0, microsecond=0)
        if next_run <= now:
            next_run += timedelta(days=1)
        return next_run
    elif cron_expression == CRON_WEEKLY_SUNDAY_2AM:  # Weekly on Sunday at 2 AM
        next_run = now.replace(hour=2, minute=0, second=0, microsecond=0)
        days_until_sunday = (6 - now.weekday()) % 7
        if days_until_sunday == 0 and next_run <= now:
            days_until_sunday = 7
        next_run += timedelta(days=days_until_sunday)
        return next_run
    
    return None


def schedule_next_run(project_id: str) -> bool:
    """
    Schedule the next run for a project based on its cron expression.
    This function creates a new run in the database and enqueues the task using Google Cloud Tasks.
    """
    try:
        data_fetcher = DataFetcher()
        
        # Get project config and domain in a single query by joining tables
        config = data_fetcher.get_project_config_with_domain(project_id)
        
        if not config:
            logger.warning(f"No config found for project {project_id}")
            return False
        
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
        
        # Create a new run in the database with QUEUED status
        new_run_id = data_fetcher.create_run(project_id)
        
        if not new_run_id:
            logger.error(f"Failed to create new run for project {project_id}")
            return False
        
        logger.info(f"Created new run {new_run_id} for project {project_id}")
        
        # Create job payload for Cloud Tasks
        job_id = f"scheduled_{project_id}_{int(next_run_time.timestamp())}"
        job_payload = {
            "id": job_id,
            "projectId": project_id,
            "url": domain,
            "priority": "scheduled",
            "render_mode": "scheduled",
            "isScheduled": True,
            "scheduledAt": int(next_run_time.timestamp() * 1000),  # Convert to milliseconds
            "runId": new_run_id,
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
        print(task_name)
        
        # Update project config with next run time and task name in a single operation
        current_time = datetime.now(timezone.utc).isoformat()
        update_success = data_fetcher.update_project_next_run(project_id, current_time, next_run_time.isoformat())
        
        if not update_success:
            logger.error(f"Failed to update next run time for project {project_id}")
            return False
        
        logger.info(f"Scheduled next run for project {project_id} at {next_run_time.isoformat()} with task {task_name}")
        return True
        
    except Exception as e:
        logger.error(f"Error scheduling next run for project {project_id}: {e}")
        return False
