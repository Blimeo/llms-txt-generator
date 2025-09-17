# apps/worker/worker/cloud_tasks_client.py
"""Google Cloud Tasks client for scheduling jobs."""

import json
import logging
import os
from datetime import datetime
from typing import Optional, Dict, Any

from google.cloud import tasks_v2
from google.protobuf import timestamp_pb2

from .constants import (
    CLOUD_TASKS_PROJECT_ID,
    CLOUD_TASKS_LOCATION,
    CLOUD_TASKS_QUEUE_NAME,
    ENV_WORKER_URL
)

logger = logging.getLogger(__name__)

class CloudTasksClient:
    """Client for managing Google Cloud Tasks"""
    
    def __init__(self):
        """Initialize the Cloud Tasks client"""
        self.client = tasks_v2.CloudTasksClient()
        self.project_id = CLOUD_TASKS_PROJECT_ID
        self.location = CLOUD_TASKS_LOCATION
        self.queue_name = CLOUD_TASKS_QUEUE_NAME
        self.queue_path = self.client.queue_path(
            CLOUD_TASKS_PROJECT_ID, CLOUD_TASKS_LOCATION, CLOUD_TASKS_QUEUE_NAME
        )
        
    def schedule_job(self, job: Dict[str, Any], scheduled_at: datetime) -> Optional[str]:
        """
        Create a Cloud Task for scheduled execution
        
        Args:
            job: Dictionary containing job data (id, projectId, runId, url, etc.)
            scheduled_at: datetime object for when the task should run
            
        Returns:
            Task name if successful, None if failed
        """
        try:
            # Get worker URL from environment
            worker_url = os.environ.get(ENV_WORKER_URL, "https://worker-service-url")
            logger.info("worker_url: %s", worker_url)
            # Convert datetime to timestamp
            timestamp = timestamp_pb2.Timestamp()
            timestamp.FromDatetime(scheduled_at)
            
            # Create task
            task = {
                "http_request": {
                    "http_method": tasks_v2.HttpMethod.POST,
                    "url": worker_url,
                    "headers": {
                        "Content-Type": "application/json",
                    },
                    "body": json.dumps(job).encode("utf-8"),
                },
                # Schedule the task for future execution
                "schedule_time": timestamp,
                # Add task name for deduplication
                "name": self.client.task_path(
                    self.project_id, 
                    self.location, 
                    self.queue_name, 
                    job["id"]
                ),
            }
            
            # Create the task
            response = self.client.create_task(
                parent=self.queue_path, 
                task=task
            )
            
            logger.info(f"Created scheduled task: {response.name} for {scheduled_at.isoformat()}")
            return response.name
            
        except Exception as e:
            logger.error(f"Error creating scheduled Cloud Task: {e}")
            return None
    


# Global client instance
_client: Optional[CloudTasksClient] = None

def get_cloud_tasks_client() -> CloudTasksClient:
    """Get or create the global Cloud Tasks client instance"""
    global _client
    if _client is None:
        _client = CloudTasksClient()
    return _client
