# apps/worker/worker/cloud_tasks_client.py
import os
import json
import logging
from typing import Optional, Dict, Any
from datetime import datetime
from google.cloud import tasks_v2
from google.protobuf import timestamp_pb2

logger = logging.getLogger(__name__)

# Configuration from scheduler.ts
PROJECT_ID = 'api-project-1042553923996'
LOCATION = 'us-west1'
QUEUE_NAME = 'llms-txt'

class CloudTasksClient:
    """Client for managing Google Cloud Tasks"""
    
    def __init__(self):
        """Initialize the Cloud Tasks client"""
        self.client = tasks_v2.CloudTasksClient()
        self.project_id = PROJECT_ID
        self.location = LOCATION
        self.queue_name = QUEUE_NAME
        self.queue_path = self.client.queue_path(PROJECT_ID, LOCATION, QUEUE_NAME)
        
    def enqueue_immediate_job(self, job: Dict[str, Any]) -> Optional[str]:
        """
        Create a Cloud Task for immediate execution
        
        Args:
            job: Dictionary containing job data (id, projectId, runId, url, etc.)
            
        Returns:
            Task name if successful, None if failed
        """
        try:
            # Get worker URL from environment
            worker_url = os.environ.get("WORKER_URL", "https://worker-service-url")
            
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
            
            logger.info(f"Created immediate task: {response.name}")
            return response.name
            
        except Exception as e:
            logger.error(f"Error creating immediate Cloud Task: {e}")
            return None
    
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
            worker_url = os.environ.get("WORKER_URL", "https://worker-service-url")
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
    
    def cancel_scheduled_job(self, job_id: str) -> bool:
        """
        Cancel a scheduled task
        
        Args:
            job_id: The ID of the job to cancel
            
        Returns:
            True if successful, False otherwise
        """
        try:
            task_name = self.client.task_path(
                self.project_id, 
                self.location, 
                self.queue_name, 
                job_id
            )
            
            self.client.delete_task(name=task_name)
            logger.info(f"Deleted task: {task_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting Cloud Task: {e}")
            return False
    
    def get_task_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get task status (optional - for monitoring)
        
        Args:
            job_id: The ID of the job to check
            
        Returns:
            Dictionary with task status info or None if failed
        """
        try:
            task_name = self.client.task_path(
                self.project_id, 
                self.location, 
                self.queue_name, 
                job_id
            )
            
            task = self.client.get_task(name=task_name)
            
            return {
                "name": task.name,
                "schedule_time": task.schedule_time,
                "create_time": task.create_time,
                "dispatch_count": task.dispatch_count,
                "response_count": task.response_count,
                "first_attempt": task.first_attempt,
                "last_attempt": task.last_attempt,
            }
            
        except Exception as e:
            logger.error(f"Error getting task status: {e}")
            return None


# Global client instance
_client: Optional[CloudTasksClient] = None

def get_cloud_tasks_client() -> CloudTasksClient:
    """Get or create the global Cloud Tasks client instance"""
    global _client
    if _client is None:
        _client = CloudTasksClient()
    return _client
