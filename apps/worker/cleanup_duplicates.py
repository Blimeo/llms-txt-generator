#!/usr/bin/env python3
"""
Script to clean up duplicate page revisions with the same content hash.

This script identifies and removes duplicate page revisions that have the same
content_sha256 hash for the same page_id, keeping only the most recent one.
"""

import os
import sys
import logging
from datetime import datetime

# Add the worker directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'worker'))

from worker.db_utils import DatabaseUtils

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def cleanup_duplicate_revisions(project_id: str = None):
    """Clean up duplicate revisions for a specific project or all projects."""
    
    logger.info("=" * 60)
    logger.info("Duplicate Page Revisions Cleanup")
    logger.info("=" * 60)
    
    try:
        db_utils = DatabaseUtils()
        
        if project_id:
            logger.info(f"Cleaning up duplicates for project: {project_id}")
            deleted_count = db_utils.cleanup_duplicate_revisions(project_id)
            logger.info(f"Cleaned up {deleted_count} duplicate revisions")
        else:
            logger.info("Cleaning up duplicates for all projects...")
            
            # Get all projects
            try:
                result = db_utils.supabase.table("projects").select("id, name").execute()
                if not result.data:
                    logger.info("No projects found")
                    return
                
                total_deleted = 0
                for project in result.data:
                    proj_id = project['id']
                    proj_name = project['name']
                    logger.info(f"Processing project: {proj_name} ({proj_id})")
                    
                    deleted_count = db_utils.cleanup_duplicate_revisions(proj_id)
                    total_deleted += deleted_count
                    logger.info(f"  Cleaned up {deleted_count} duplicates")
                
                logger.info(f"Total duplicates cleaned up: {total_deleted}")
                
            except Exception as e:
                logger.error(f"Failed to get projects: {e}")
                return
        
        logger.info("Cleanup completed successfully!")
        
    except Exception as e:
        logger.error(f"Cleanup failed: {e}")
        import traceback
        traceback.print_exc()


def analyze_duplicates(project_id: str = None):
    """Analyze duplicate revisions without cleaning them up."""
    
    logger.info("=" * 60)
    logger.info("Duplicate Page Revisions Analysis")
    logger.info("=" * 60)
    
    try:
        db_utils = DatabaseUtils()
        
        if project_id:
            logger.info(f"Analyzing duplicates for project: {project_id}")
            
            # Get all page revisions for the project
            result = db_utils.supabase.table("page_revisions").select(
                "id, page_id, content_sha256, created_at, pages!inner(project_id, url)"
            ).eq("pages.project_id", project_id).order("created_at", desc=True).execute()
            
            if not result.data:
                logger.info("No revisions found for this project")
                return
            
            # Group by page_id and content_sha256
            revisions_by_page_and_hash = {}
            for revision in result.data:
                key = f"{revision['page_id']}_{revision['content_sha256']}"
                if key not in revisions_by_page_and_hash:
                    revisions_by_page_and_hash[key] = []
                revisions_by_page_and_hash[key].append(revision)
            
            # Find duplicates
            duplicates_found = 0
            for key, revisions in revisions_by_page_and_hash.items():
                if len(revisions) > 1:
                    duplicates_found += len(revisions) - 1
                    page_url = revisions[0].get('pages', {}).get('url', 'Unknown')
                    logger.info(f"Found {len(revisions)} revisions for page {page_url} with hash {revisions[0]['content_sha256'][:8]}...")
                    for i, rev in enumerate(revisions):
                        status = "KEEP" if i == 0 else "DELETE"
                        logger.info(f"  {status}: {rev['id']} - {rev['created_at']}")
            
            logger.info(f"Total duplicate revisions found: {duplicates_found}")
            
        else:
            logger.info("Analyzing duplicates for all projects...")
            
            # Get all projects
            try:
                result = db_utils.supabase.table("projects").select("id, name").execute()
                if not result.data:
                    logger.info("No projects found")
                    return
                
                total_duplicates = 0
                for project in result.data:
                    proj_id = project['id']
                    proj_name = project['name']
                    
                    # Get revision count for this project
                    rev_result = db_utils.supabase.table("page_revisions").select(
                        "id, page_id, content_sha256, created_at, pages!inner(project_id)"
                    ).eq("pages.project_id", proj_id).execute()
                    
                    if rev_result.data:
                        # Group by page_id and content_sha256
                        revisions_by_page_and_hash = {}
                        for revision in rev_result.data:
                            key = f"{revision['page_id']}_{revision['content_sha256']}"
                            if key not in revisions_by_page_and_hash:
                                revisions_by_page_and_hash[key] = []
                            revisions_by_page_and_hash[key].append(revision)
                        
                        # Count duplicates
                        project_duplicates = 0
                        for key, revisions in revisions_by_page_and_hash.items():
                            if len(revisions) > 1:
                                project_duplicates += len(revisions) - 1
                        
                        total_duplicates += project_duplicates
                        logger.info(f"Project {proj_name}: {project_duplicates} duplicates out of {len(rev_result.data)} total revisions")
                
                logger.info(f"Total duplicates across all projects: {total_duplicates}")
                
            except Exception as e:
                logger.error(f"Failed to analyze projects: {e}")
                return
        
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Clean up duplicate page revisions")
    parser.add_argument("--project-id", help="Specific project ID to clean up")
    parser.add_argument("--analyze-only", action="store_true", help="Only analyze duplicates, don't clean up")
    
    args = parser.parse_args()
    
    if args.analyze_only:
        analyze_duplicates(args.project_id)
    else:
        cleanup_duplicate_revisions(args.project_id)
