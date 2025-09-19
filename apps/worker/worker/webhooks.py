# apps/worker/worker/webhooks.py
"""Webhook management and execution."""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional

import requests

from .constants import (
    WEBHOOK_TIMEOUT,
    WEBHOOK_USER_AGENT,
    WEBHOOK_HEADER_SECRET,
    WEBHOOK_CONTENT_TYPE
)
from .data_fetcher import DataFetcher

logger = logging.getLogger(__name__)


def call_webhooks_for_project(project_id: str, run_id: str, llms_txt_url: str) -> None:
    """
    Call all active webhooks for a project when llms.txt is generated.
    
    Args:
        project_id: The project ID
        run_id: The run ID that generated the llms.txt
        llms_txt_url: The URL to the generated llms.txt file
    """
    try:
        data_fetcher = DataFetcher()
        
        # Get all active webhooks for the project
        webhooks = data_fetcher.get_active_webhooks(project_id)
        
        if not webhooks:
            logger.info(f"No active webhooks found for project {project_id}")
            return
        
        logger.info(f"Found {len(webhooks)} active webhooks for project {project_id}")
        
        # Prepare the webhook payload
        payload = {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "llms_txt_url": llms_txt_url
        }
        
        # Call each webhook
        for webhook in webhooks:
            call_single_webhook(data_fetcher, webhook, payload, run_id)
            
    except Exception as e:
        logger.error(f"Error calling webhooks for project {project_id}: {e}")


def call_single_webhook(data_fetcher: DataFetcher, webhook: Dict[str, Any], payload: Dict[str, Any], run_id: str) -> None:
    """
    Call a single webhook and log the result.
    
    Args:
        data_fetcher: The data fetcher instance
        webhook: The webhook configuration from the database
        payload: The payload to send to the webhook
        run_id: The run ID for logging purposes
    """
    webhook_id = webhook["id"]
    webhook_url = webhook["url"]
    webhook_secret = webhook.get("secret")
    
    try:
        # Prepare headers
        headers = {
            "Content-Type": WEBHOOK_CONTENT_TYPE,
            "User-Agent": WEBHOOK_USER_AGENT
        }
        
        # Add secret to headers if provided
        if webhook_secret:
            headers[WEBHOOK_HEADER_SECRET] = webhook_secret
        
        # Make the HTTP request
        logger.info(f"Calling webhook {webhook_id} at {webhook_url}")
        response = requests.post(
            webhook_url,
            json=payload,
            headers=headers,
            timeout=WEBHOOK_TIMEOUT
        )
        
        # Log the webhook event
        log_webhook_event(
            data_fetcher=data_fetcher,
            webhook_id=webhook_id,
            event_type="run.complete",
            payload=payload,
            status_code=response.status_code,
            response_body=response.text[:1000] if response.text else None,  # Limit response body length
            run_id=run_id
        )
        
        if response.status_code >= 200 and response.status_code < 300:
            logger.info(f"Webhook {webhook_id} called successfully (status: {response.status_code})")
        else:
            logger.warning(f"Webhook {webhook_id} returned error status: {response.status_code}")
            
    except requests.exceptions.Timeout:
        logger.error(f"Webhook {webhook_id} timed out after {WEBHOOK_TIMEOUT} seconds")
        log_webhook_event(
            data_fetcher=data_fetcher,
            webhook_id=webhook_id,
            event_type="run.complete",
            payload=payload,
            status_code=None,
            response_body="Request timeout",
            run_id=run_id
        )
    except requests.exceptions.RequestException as e:
        logger.error(f"Webhook {webhook_id} request failed: {e}")
        log_webhook_event(
            data_fetcher=data_fetcher,
            webhook_id=webhook_id,
            event_type="run.complete",
            payload=payload,
            status_code=None,
            response_body=str(e),
            run_id=run_id
        )
    except Exception as e:
        logger.error(f"Unexpected error calling webhook {webhook_id}: {e}")
        log_webhook_event(
            data_fetcher=data_fetcher,
            webhook_id=webhook_id,
            event_type="run.complete",
            payload=payload,
            status_code=None,
            response_body=str(e),
            run_id=run_id
        )


def log_webhook_event(data_fetcher: DataFetcher, webhook_id: str, event_type: str, payload: Dict[str, Any], 
                     status_code: Optional[int], response_body: Optional[str], run_id: str) -> None:
    """
    Log webhook event to the webhook_events table.
    
    Args:
        data_fetcher: The data fetcher instance
        webhook_id: The webhook ID
        event_type: The event type (e.g., "run.complete")
        payload: The payload that was sent
        status_code: HTTP status code returned (None if request failed)
        response_body: Response body (truncated if too long)
        run_id: The run ID for context
    """
    try:
        success = data_fetcher.log_webhook_event(webhook_id, event_type, payload, status_code, response_body)
        
        if success:
            logger.debug(f"Logged webhook event for webhook {webhook_id}")
        else:
            logger.error(f"Failed to log webhook event for webhook {webhook_id}")
            
    except Exception as e:
        logger.error(f"Error logging webhook event for webhook {webhook_id}: {e}")
