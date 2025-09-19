# apps/worker/worker/data_fetcher.py
"""Data fetcher module to handle all Supabase database operations."""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple

from .database import get_supabase_client
from .constants import (
    TABLE_PAGES,
    TABLE_PAGE_REVISIONS,
    TABLE_PROJECTS,
    TABLE_PROJECT_CONFIGS,
    TABLE_RUNS,
    TABLE_ARTIFACTS,
    TABLE_WEBHOOKS,
    TABLE_WEBHOOK_EVENTS,
    ARTIFACT_TYPE_LLMS_TXT,
    RUN_STATUS_IN_PROGRESS,
    RUN_STATUS_COMPLETE_NO_DIFFS,
    RUN_STATUS_COMPLETE_WITH_DIFFS,
    RUN_STATUS_FAILED
)

logger = logging.getLogger(__name__)


class DataFetcher:
    """
    Centralized data fetcher for all Supabase database operations.
    This class handles all database interactions, allowing business logic
    to be tested by mocking this class instead of the Supabase client.
    """
    
    def __init__(self):
        self.supabase = get_supabase_client()
    
    # Project and Configuration Operations
    def get_project_config_with_domain(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Get project configuration with domain information."""
        try:
            result = self.supabase.table(TABLE_PROJECT_CONFIGS).select(
                "cron_expression, is_enabled, next_run_at, projects!inner(domain)"
            ).eq("project_id", project_id).single().execute()
            
            return result.data if result.data else None
        except Exception as e:
            logger.error(f"Error fetching project config for {project_id}: {e}")
            return None
    
    def update_project_last_run(self, project_id: str, last_run_at: str) -> bool:
        """Update the last_run_at timestamp for a project."""
        try:
            result = self.supabase.table(TABLE_PROJECT_CONFIGS).update({
                "last_run_at": last_run_at
            }).eq("project_id", project_id).execute()
            
            return bool(result.data)
        except Exception as e:
            logger.error(f"Error updating last_run_at for project {project_id}: {e}")
            return False
    
    def update_project_next_run(self, project_id: str, last_run_at: str, next_run_at: str) -> bool:
        """Update both last_run_at and next_run_at for a project."""
        try:
            result = self.supabase.table(TABLE_PROJECT_CONFIGS).update({
                "last_run_at": last_run_at,
                "next_run_at": next_run_at
            }).eq("project_id", project_id).execute()
            
            return bool(result.data)
        except Exception as e:
            logger.error(f"Error updating run times for project {project_id}: {e}")
            return False
    
    # Run Operations
    def create_run(self, project_id: str) -> Optional[str]:
        """Create a new run in the database and return the run ID."""
        try:
            result = self.supabase.table(TABLE_RUNS).insert({
                "project_id": project_id,
                "status": "QUEUED",
                "created_at": datetime.now(timezone.utc).isoformat()
            }).execute()
            
            if result.data:
                return result.data[0]["id"]
            return None
        except Exception as e:
            logger.error(f"Error creating run for project {project_id}: {e}")
            return None
    
    def update_run_status(self, run_id: str, status: str, summary: str = None, 
                         finished_at: str = None) -> bool:
        """Update run status in the database."""
        try:
            update_data = {
                "status": status,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            
            if status in [RUN_STATUS_COMPLETE_NO_DIFFS, RUN_STATUS_COMPLETE_WITH_DIFFS, RUN_STATUS_FAILED]:
                update_data["finished_at"] = finished_at or datetime.now(timezone.utc).isoformat()
                if summary:
                    if status == RUN_STATUS_FAILED:
                        update_data["summary"] = f"Generation failed: {summary}"
                    else:
                        update_data["summary"] = summary
                elif status == RUN_STATUS_FAILED:
                    update_data["summary"] = "Generation failed"
            
            result = self.supabase.table(TABLE_RUNS).update(update_data).eq("id", run_id).execute()
            return bool(result.data)
        except Exception as e:
            logger.error(f"Error updating run {run_id} status: {e}")
            return False
    
    # Page Operations
    def get_existing_pages_with_revisions(self, project_id: str) -> List[Dict[str, Any]]:
        """Get existing pages from database with their current revision info."""
        try:
            # First get all pages
            result = self.supabase.table(TABLE_PAGES).select(
                "id, url, path, canonical_url, current_revision_id, last_seen_at, render_mode, is_indexable, metadata"
            ).eq("project_id", project_id).execute()
            
            if not result.data:
                return []
            
            pages = result.data
            
            # Get current revisions for all pages in a batch
            current_revision_ids = [page['current_revision_id'] for page in pages if page.get('current_revision_id')]
            
            revisions = {}
            if current_revision_ids:
                rev_result = self.supabase.table(TABLE_PAGE_REVISIONS).select(
                    "id, page_id, content_sha256, created_at, metadata"
                ).in_("id", current_revision_ids).execute()
                
                if rev_result.data:
                    for revision in rev_result.data:
                        revisions[revision['id']] = revision
            
            # Attach current revision info to each page
            for page in pages:
                current_revision_id = page.get('current_revision_id')
                if current_revision_id and current_revision_id in revisions:
                    page['current_revision'] = revisions[current_revision_id]
                else:
                    page['current_revision'] = None
            
            return pages
        except Exception as e:
            logger.error(f"Error getting existing pages with revisions: {e}")
            return []
    
    def create_page_record(self, project_id: str, page_info: Dict[str, Any]) -> Optional[str]:
        """Create a new page record in the database."""
        try:
            page_data = {
                'project_id': project_id,
                'url': page_info['url'],
                'path': page_info.get('path', '/'),
                'canonical_url': page_info.get('canonical_url', page_info['url']),
                'render_mode': page_info.get('render_mode', 'STATIC'),
                'is_indexable': page_info.get('is_indexable', True),
                'discovered_at': datetime.now(timezone.utc).isoformat(),
                'metadata': page_info.get('metadata', {})
            }
            
            result = self.supabase.table(TABLE_PAGES).insert(page_data).execute()
            
            if result.data:
                return result.data[0]['id']
            return None
        except Exception as e:
            logger.error(f"Error creating page record: {e}")
            return None
    
    def update_page_last_seen(self, page_id: str) -> bool:
        """Update the last_seen_at timestamp for a page."""
        try:
            result = self.supabase.table(TABLE_PAGES).update({
                'last_seen_at': datetime.now(timezone.utc).isoformat()
            }).eq('id', page_id).execute()
            
            return bool(result.data)
        except Exception as e:
            logger.error(f"Error updating last_seen_at for page {page_id}: {e}")
            return False
    
    def update_page_revision(self, page_id: str, revision_id: str) -> bool:
        """Update a page's current_revision_id and last_seen_at."""
        try:
            result = self.supabase.table(TABLE_PAGES).update({
                'current_revision_id': revision_id,
                'last_seen_at': datetime.now(timezone.utc).isoformat()
            }).eq('id', page_id).execute()
            
            return bool(result.data)
        except Exception as e:
            logger.error(f"Error updating page revision for {page_id}: {e}")
            return False
    
    # Page Revision Operations
    def get_revision_by_id(self, revision_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific revision by ID."""
        try:
            result = self.supabase.table(TABLE_PAGE_REVISIONS).select("*").eq(
                "id", revision_id
            ).execute()
            
            if result.data and len(result.data) > 0:
                return result.data[0]
            return None
        except Exception as e:
            logger.error(f"Error getting revision {revision_id}: {e}")
            return None
    
    def create_page_revision(self, page_id: str, run_id: str, content: str, 
                           content_hash: str, title: str = "", description: str = "", 
                           metadata: Dict = None) -> Optional[str]:
        """Create a new page revision in the database."""
        try:
            revision_data = {
                'page_id': page_id,
                'run_id': run_id,
                'content': content,
                'content_sha256': content_hash,
                'title': title,
                'meta_description': description,
                'metadata': metadata or {}
            }
            
            result = self.supabase.table(TABLE_PAGE_REVISIONS).insert(revision_data).execute()
            
            if result.data:
                return result.data[0]['id']
            return None
        except Exception as e:
            logger.error(f"Error creating page revision: {e}")
            return None
    
    # Artifact Operations
    def get_latest_llms_txt_url(self, project_id: str) -> Optional[str]:
        """Get the most recent llms.txt URL from the artifacts table for a project."""
        try:
            result = self.supabase.table(TABLE_ARTIFACTS).select("metadata").eq(
                "project_id", project_id
            ).eq("type", ARTIFACT_TYPE_LLMS_TXT).order("created_at", desc=True).limit(1).execute()
            
            if result.data and len(result.data) > 0:
                metadata = result.data[0].get("metadata", {})
                return metadata.get("public_url")
            return None
        except Exception as e:
            logger.error(f"Error getting latest llms.txt URL for project {project_id}: {e}")
            return None
    
    def create_artifact_record(self, project_id: str, run_id: str, filename: str, 
                             content: str, public_url: str) -> Optional[str]:
        """Create an artifact record in the database."""
        try:
            file_size = len(content.encode('utf-8'))
            
            artifact_data = {
                "project_id": project_id,
                "run_id": run_id,
                "type": ARTIFACT_TYPE_LLMS_TXT,
                "storage_path": f"s3://llms-txt/{filename}",
                "file_name": filename,
                "size_bytes": file_size,
                "metadata": {
                    "public_url": public_url,
                    "bucket": "llms-txt",
                    "key": filename,
                    "uploaded_at": datetime.now(timezone.utc).isoformat()
                }
            }
            
            result = self.supabase.table(TABLE_ARTIFACTS).insert(artifact_data).execute()
            
            if result.data:
                return result.data[0]['id']
            return None
        except Exception as e:
            logger.error(f"Error creating artifact record: {e}")
            return None
    
    # Webhook Operations
    def get_active_webhooks(self, project_id: str) -> List[Dict[str, Any]]:
        """Get all active webhooks for a project."""
        try:
            result = self.supabase.table(TABLE_WEBHOOKS).select("*").eq(
                "project_id", project_id
            ).eq("is_active", True).execute()
            
            return result.data if result.data else []
        except Exception as e:
            logger.error(f"Error getting active webhooks for project {project_id}: {e}")
            return []
    
    def log_webhook_event(self, webhook_id: str, event_type: str, payload: Dict[str, Any], 
                         status_code: Optional[int], response_body: Optional[str]) -> bool:
        """Log webhook event to the webhook_events table."""
        try:
            event_data = {
                "webhook_id": webhook_id,
                "event_type": event_type,
                "payload": payload,
                "status_code": status_code,
                "response_body": response_body,
                "attempted_at": datetime.now(timezone.utc).isoformat()
            }
            
            result = self.supabase.table(TABLE_WEBHOOK_EVENTS).insert(event_data).execute()
            return bool(result.data)
        except Exception as e:
            logger.error(f"Error logging webhook event for webhook {webhook_id}: {e}")
            return False
