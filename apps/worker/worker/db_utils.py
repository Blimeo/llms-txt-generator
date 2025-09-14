# apps/worker/worker/db_utils.py
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from .storage import get_supabase_client

logger = logging.getLogger(__name__)


class DatabaseUtils:
    """Utility functions for database operations related to change detection."""
    
    def __init__(self):
        self.supabase = get_supabase_client()
    
    def get_project_pages(self, project_id: str) -> List[Dict]:
        """Get all pages for a project with their current revision info."""
        try:
            result = self.supabase.table("pages").select(
                "id, url, path, canonical_url, current_revision_id, last_seen_at, "
                "render_mode, is_indexable, metadata, page_revisions(id, content_sha256, created_at)"
            ).eq("project_id", project_id).execute()
            
            if result.data:
                return result.data
            return []
        except Exception as e:
            logger.error(f"Failed to get project pages: {e}")
            return []
    
    def get_page_revisions(self, page_id: str, limit: int = 10) -> List[Dict]:
        """Get recent revisions for a page."""
        try:
            result = self.supabase.table("page_revisions").select("*").eq(
                "page_id", page_id
            ).order("created_at", desc=True).limit(limit).execute()
            
            if result.data:
                return result.data
            return []
        except Exception as e:
            logger.error(f"Failed to get page revisions for {page_id}: {e}")
            return []
    
    def create_diff_record(self, run_id: str, page_id: str, from_revision_id: str, 
                          to_revision_id: str, change_type: str, summary: str = None) -> Optional[str]:
        """Create a diff record between two page revisions."""
        try:
            diff_data = {
                "run_id": run_id,
                "page_id": page_id,
                "from_revision_id": from_revision_id,
                "to_revision_id": to_revision_id,
                "change_type": change_type,
                "summary": summary,
                "metadata": {}
            }
            
            result = self.supabase.table("diffs").insert(diff_data).execute()
            
            if result.data:
                diff_id = result.data[0]["id"]
                logger.info(f"Created diff record {diff_id} for page {page_id}")
                return diff_id
            else:
                logger.error(f"Failed to create diff record for page {page_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error creating diff record for page {page_id}: {e}")
            return None
    
    def update_run_metrics(self, run_id: str, metrics: Dict[str, Any]) -> bool:
        """Update run with metrics about the crawl."""
        try:
            result = self.supabase.table("runs").update({
                "metrics": metrics,
                "updated_at": datetime.utcnow().isoformat()
            }).eq("id", run_id).execute()
            
            if result.data:
                logger.info(f"Updated run {run_id} metrics")
                return True
            else:
                logger.error(f"Failed to update run {run_id} metrics")
                return False
                
        except Exception as e:
            logger.error(f"Error updating run metrics: {e}")
            return False
    
    def get_run_summary(self, run_id: str) -> Optional[Dict]:
        """Get summary information about a run."""
        try:
            result = self.supabase.table("runs").select(
                "id, project_id, status, started_at, finished_at, summary, metrics"
            ).eq("id", run_id).execute()
            
            if result.data:
                return result.data[0]
            return None
        except Exception as e:
            logger.error(f"Failed to get run summary for {run_id}: {e}")
            return None
    
    def mark_pages_as_unchanged(self, run_id: str, unchanged_page_ids: List[str]) -> bool:
        """Mark pages as unchanged in the current run."""
        try:
            if not unchanged_page_ids:
                return True
            
            # Create diff records for unchanged pages
            diff_records = []
            for page_id in unchanged_page_ids:
                diff_records.append({
                    "run_id": run_id,
                    "page_id": page_id,
                    "from_revision_id": None,
                    "to_revision_id": None,
                    "change_type": "UNCHANGED",
                    "summary": "No changes detected",
                    "metadata": {}
                })
            
            result = self.supabase.table("diffs").insert(diff_records).execute()
            
            if result.data:
                logger.info(f"Marked {len(unchanged_page_ids)} pages as unchanged")
                return True
            else:
                logger.error("Failed to mark pages as unchanged")
                return False
                
        except Exception as e:
            logger.error(f"Error marking pages as unchanged: {e}")
            return False
    
    def get_sitemap_urls(self, project_id: str) -> List[str]:
        """Get cached sitemap URLs for a project if available."""
        try:
            result = self.supabase.table("projects").select("metadata").eq("id", project_id).execute()
            
            if result.data and result.data[0].get("metadata"):
                metadata = result.data[0]["metadata"]
                return metadata.get("sitemap_urls", [])
            return []
        except Exception as e:
            logger.error(f"Failed to get sitemap URLs for project {project_id}: {e}")
            return []
    
    def cache_sitemap_urls(self, project_id: str, urls: List[str]) -> bool:
        """Cache sitemap URLs in project metadata."""
        try:
            result = self.supabase.table("projects").update({
                "metadata": {
                    "sitemap_urls": urls,
                    "sitemap_cached_at": datetime.utcnow().isoformat()
                }
            }).eq("id", project_id).execute()
            
            if result.data:
                logger.info(f"Cached {len(urls)} sitemap URLs for project {project_id}")
                return True
            else:
                logger.error(f"Failed to cache sitemap URLs for project {project_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error caching sitemap URLs: {e}")
            return False
    
    def get_page_by_url(self, project_id: str, url: str) -> Optional[Dict]:
        """Get a specific page by URL for a project."""
        try:
            result = self.supabase.table("pages").select(
                "id, url, path, canonical_url, current_revision_id, last_seen_at, "
                "render_mode, is_indexable, metadata, page_revisions!current_revision_id(id, content_sha256, created_at, metadata)"
            ).eq("project_id", project_id).eq("url", url).execute()
            
            if result.data and len(result.data) > 0:
                return result.data[0]
            return None
        except Exception as e:
            logger.error(f"Failed to get page by URL {url}: {e}")
            return None
    
    def batch_get_page_revisions(self, page_ids: List[str]) -> Dict[str, List[Dict]]:
        """Get revisions for multiple pages in a single query."""
        try:
            if not page_ids:
                return {}
            
            result = self.supabase.table("page_revisions").select(
                "id, page_id, content_sha256, created_at, metadata"
            ).in_("page_id", page_ids).order("created_at", desc=True).execute()
            
            # Group by page_id
            revisions_by_page = {}
            if result.data:
                for revision in result.data:
                    page_id = revision['page_id']
                    if page_id not in revisions_by_page:
                        revisions_by_page[page_id] = []
                    revisions_by_page[page_id].append(revision)
            
            return revisions_by_page
        except Exception as e:
            logger.error(f"Failed to batch get page revisions: {e}")
            return {}
    
    def update_run_status(self, run_id: str, status: str, summary: str = None) -> bool:
        """Update run status and optionally summary."""
        try:
            update_data = {
                "status": status,
                "updated_at": datetime.utcnow().isoformat()
            }
            
            if summary:
                update_data["summary"] = summary
            
            if status in ["COMPLETE_NO_DIFFS", "COMPLETE_WITH_DIFFS"]:
                update_data["finished_at"] = datetime.utcnow().isoformat()
            
            result = self.supabase.table("runs").update(update_data).eq("id", run_id).execute()
            
            if result.data:
                logger.info(f"Updated run {run_id} status to {status}")
                return True
            else:
                logger.error(f"Failed to update run {run_id} status")
                return False
                
        except Exception as e:
            logger.error(f"Error updating run status: {e}")
            return False
    
    def find_duplicate_revisions(self, project_id: str) -> List[Dict]:
        """Find duplicate page revisions with the same content hash."""
        try:
            # Query to find duplicates
            result = self.supabase.rpc('find_duplicate_revisions', {
                'project_id': project_id
            }).execute()
            
            if result.data:
                return result.data
            return []
        except Exception as e:
            logger.error(f"Failed to find duplicate revisions: {e}")
            return []
    
    def cleanup_duplicate_revisions(self, project_id: str) -> int:
        """Clean up duplicate revisions, keeping only the most recent one for each page/hash combination."""
        try:
            # Get all page revisions for the project
            result = self.supabase.table("page_revisions").select(
                "id, page_id, content_sha256, created_at"
            ).eq("page_id", "pages!inner(project_id)", project_id).order("created_at", desc=True).execute()
            
            if not result.data:
                return 0
            
            # Group by page_id and content_sha256
            revisions_by_page_and_hash = {}
            for revision in result.data:
                key = f"{revision['page_id']}_{revision['content_sha256']}"
                if key not in revisions_by_page_and_hash:
                    revisions_by_page_and_hash[key] = []
                revisions_by_page_and_hash[key].append(revision)
            
            # Find duplicates and delete older ones
            deleted_count = 0
            for key, revisions in revisions_by_page_and_hash.items():
                if len(revisions) > 1:
                    # Keep the most recent (first in the list since we ordered by created_at desc)
                    keep_revision = revisions[0]
                    duplicates = revisions[1:]
                    
                    # Delete duplicates
                    for duplicate in duplicates:
                        try:
                            delete_result = self.supabase.table("page_revisions").delete().eq(
                                "id", duplicate['id']
                            ).execute()
                            
                            if delete_result.data:
                                deleted_count += 1
                                logger.info(f"Deleted duplicate revision {duplicate['id']} for page {duplicate['page_id']}")
                        except Exception as e:
                            logger.warning(f"Failed to delete duplicate revision {duplicate['id']}: {e}")
            
            logger.info(f"Cleaned up {deleted_count} duplicate revisions for project {project_id}")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error cleaning up duplicate revisions: {e}")
            return 0