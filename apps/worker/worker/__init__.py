# apps/worker/worker/__init__.py
"""
LLMS.txt Worker Package

This package provides web crawling, change detection, and LLMS.txt generation
functionality for the llmstxt-crawler application.

Modules:
- crawler: Web crawling with change detection
- change_detection: Content change detection using headers and hashing
- llms_generator: Generate LLMS.txt formatted content
- storage: S3 uploads, database operations, and scheduling
- cloud_tasks_client: Google Cloud Tasks integration
- constants: Application constants and configuration
"""

from .crawler import crawl_with_change_detection
from .change_detection import ChangeDetector
from .llms_generator import generate_llms_text
from .storage import update_run_status, maybe_upload_s3_from_memory
from .database import get_supabase_client
from .s3_storage import upload_content_to_s3
from .webhooks import call_webhooks_for_project
from .scheduling import schedule_next_run, calculate_next_run_time
from .cloud_tasks_client import get_cloud_tasks_client

__version__ = "0.1.0"
__all__ = [
    "crawl_with_change_detection",
    "ChangeDetector", 
    "generate_llms_text",
    "get_supabase_client",
    "update_run_status",
    "maybe_upload_s3_from_memory",
    "upload_content_to_s3",
    "call_webhooks_for_project",
    "schedule_next_run",
    "calculate_next_run_time",
    "get_cloud_tasks_client",
]
