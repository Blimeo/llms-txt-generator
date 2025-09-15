# apps/worker/worker/change_detection.py
import hashlib
import logging
import requests
from typing import Dict, List, Optional, Set, Tuple
from urllib.parse import urlparse, urljoin
from datetime import datetime
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup

from .storage import get_supabase_client
from .db_utils import DatabaseUtils

logger = logging.getLogger(__name__)


class ChangeDetector:
    """
    Implements change detection following step 1 of the specification:
    1. Sitemap + Headers first: If site has sitemap.xml, fetch and use LastMod / URLs; 
       request HEAD for ETag/Last-Modified; if unchanged, skip heavy fetch.
    2. Hash-based diff: For fetched HTML (post-render if needed), compute SHA256 of the 
       normalized important content (strip timestamp-like content). Save hash in DB; 
       if changed — enqueue generation via Cloud Tasks for Python workers to process.
    """
    
    def __init__(self, project_id: str, run_id: str):
        self.project_id = project_id
        self.run_id = run_id
        self.supabase = get_supabase_client()
        self.db_utils = DatabaseUtils()
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "llms-txt-crawler/1.0 (+https://example.com)"
        })
    
    def detect_changes(self, base_url: str) -> Dict[str, any]:
        """
        Main entry point for change detection.
        Returns dict with:
        - has_changes: bool
        - changed_pages: List[Dict] - pages that have changed
        - new_pages: List[Dict] - newly discovered pages
        - unchanged_pages: List[Dict] - pages that haven't changed
        """
        logger.info(f"Starting change detection for project {self.project_id}")
        
        # Step 1: Check sitemap and headers first
        sitemap_urls = self._fetch_sitemap_urls(base_url)
        logger.info(f"Found {len(sitemap_urls)} URLs in sitemap")
        
        # Get existing pages from database with their current revisions
        existing_pages = self._get_existing_pages_with_revisions()
        existing_urls = {page['url'] for page in existing_pages}
        logger.info(f"Found {len(existing_pages)} existing pages in database")
        
        # Step 2: Hash-based diff for fetched HTML content
        # Batch process all URLs to minimize DB calls
        all_urls = set(sitemap_urls) | existing_urls
        if not all_urls and not existing_pages:
            # If no sitemap URLs and no existing pages, treat the base URL as new
            logger.info("No sitemap or existing pages found, treating base URL as new page")
            all_urls = {base_url}
        
        # Process all URLs in batches for efficiency
        changed_pages = []
        unchanged_pages = []
        new_pages = []
        
        # Process URLs in batches
        batch_size = 10
        url_list = list(all_urls)
        
        for i in range(0, len(url_list), batch_size):
            batch_urls = url_list[i:i + batch_size]
            logger.info(f"Processing batch {i//batch_size + 1}/{(len(url_list) + batch_size - 1)//batch_size}")
            
            batch_results = self._process_url_batch(batch_urls, existing_pages, sitemap_urls)
            changed_pages.extend(batch_results['changed'])
            unchanged_pages.extend(batch_results['unchanged'])
            new_pages.extend(batch_results['new'])
        
        # Cache sitemap URLs for future use
        if sitemap_urls:
            self.db_utils.cache_sitemap_urls(self.project_id, sitemap_urls)
        
        has_changes = len(changed_pages) > 0 or len(new_pages) > 0
        
        result = {
            'has_changes': has_changes,
            'changed_pages': changed_pages,
            'new_pages': new_pages,
            'unchanged_pages': unchanged_pages,
            'total_checked': len(all_urls)
        }
        
        logger.info(f"Change detection complete: {len(changed_pages)} changed, "
                   f"{len(new_pages)} new, {len(unchanged_pages)} unchanged")
        logger.info(f"Has changes: {has_changes}")
        if new_pages:
            logger.info(f"New pages: {[p['url'] for p in new_pages]}")
        if changed_pages:
            logger.info(f"Changed pages: {[p['url'] for p in changed_pages]}")
        
        # Mark unchanged pages
        self.mark_unchanged_pages(unchanged_pages)
        
        return result
    
    def _fetch_sitemap_urls(self, base_url: str) -> List[str]:
        """Fetch URLs from sitemap.xml if available."""
        parsed = urlparse(base_url)
        sitemap_url = f"{parsed.scheme}://{parsed.netloc}/sitemap.xml"
        
        try:
            response = self.session.get(sitemap_url, timeout=10)
            if response.status_code == 200:
                return self._parse_sitemap(response.text)
        except Exception as e:
            logger.warning(f"Failed to fetch sitemap {sitemap_url}: {e}")
        
        return []
    
    def _parse_sitemap(self, sitemap_xml: str) -> List[str]:
        """Parse sitemap XML and extract URLs."""
        urls = []
        try:
            root = ET.fromstring(sitemap_xml)
            
            # Handle both sitemap and sitemapindex
            if root.tag.endswith('sitemapindex'):
                # This is a sitemap index, get individual sitemaps
                for sitemap in root.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}sitemap'):
                    loc = sitemap.find('{http://www.sitemaps.org/schemas/sitemap/0.9}loc')
                    if loc is not None:
                        # Fetch individual sitemap
                        try:
                            sub_response = self.session.get(loc.text, timeout=10)
                            if sub_response.status_code == 200:
                                urls.extend(self._parse_sitemap(sub_response.text))
                        except Exception as e:
                            logger.warning(f"Failed to fetch sub-sitemap {loc.text}: {e}")
            else:
                # Regular sitemap
                for url in root.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}url'):
                    loc = url.find('{http://www.sitemaps.org/schemas/sitemap/0.9}loc')
                    if loc is not None:
                        urls.append(loc.text)
        except ET.ParseError as e:
            logger.warning(f"Failed to parse sitemap XML: {e}")
        
        return urls
    
    def _get_existing_pages_with_revisions(self) -> List[Dict]:
        """Get existing pages from database with their current revision info."""
        try:
            # First get all pages
            result = self.supabase.table("pages").select(
                "id, url, path, canonical_url, current_revision_id, last_seen_at, render_mode, is_indexable, metadata"
            ).eq("project_id", self.project_id).execute()
            
            if not result.data:
                return []
            
            pages = result.data
            
            # Get current revisions for all pages in a batch
            page_ids = [page['id'] for page in pages]
            current_revision_ids = [page['current_revision_id'] for page in pages if page.get('current_revision_id')]
            
            revisions = {}
            if current_revision_ids:
                rev_result = self.supabase.table("page_revisions").select(
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
                    logger.debug(f"Page {page['url']} has current revision {current_revision_id}")
                else:
                    page['current_revision'] = None
                    logger.debug(f"Page {page['url']} has no current revision (current_revision_id: {current_revision_id})")
            
            logger.info(f"Retrieved {len(pages)} pages with revisions")
            return pages
        except Exception as e:
            logger.error(f"Failed to get existing pages with revisions: {e}")
            return []
    
    def _process_url_batch(self, urls: List[str], existing_pages: List[Dict], sitemap_urls: List[str]) -> Dict[str, List[Dict]]:
        """Process a batch of URLs for change detection."""
        changed_pages = []
        unchanged_pages = []
        new_pages = []
        
        # Create lookup for existing pages
        existing_pages_by_url = {page['url']: page for page in existing_pages}
        
        for url in urls:
            try:
                if url in existing_pages_by_url:
                    # Existing page - check for changes
                    existing_page = existing_pages_by_url[url]
                    change_result = self._check_page_changes(url, existing_page)
                    
                    if change_result['has_changed']:
                        changed_pages.append({
                            **existing_page,
                            'change_reason': change_result['reason'],
                            'old_revision_id': change_result.get('old_revision_id')
                        })
                    else:
                        unchanged_pages.append(existing_page)
                else:
                    # New page
                    new_pages.append(self._get_page_info(url))
                    
            except Exception as e:
                logger.warning(f"Error processing URL {url}: {e}")
                # If we can't process, treat as new to be safe
                new_pages.append(self._get_page_info(url))
        
        return {
            'changed': changed_pages,
            'unchanged': unchanged_pages,
            'new': new_pages
        }
    
    def _check_page_changes(self, url: str, existing_page: Dict) -> Dict[str, any]:
        """
        Check if a page has changed using HEAD request for headers,
        then full fetch if headers suggest changes.
        Returns detailed change information.
        """
        try:
            # First, try HEAD request to check headers
            head_response = self.session.head(url, timeout=10, allow_redirects=True)
            
            if head_response.status_code != 200:
                logger.info(f"Page {url} returned {head_response.status_code}, considering as changed")
                return {
                    'has_changed': True,
                    'reason': f'HTTP {head_response.status_code}',
                    'old_revision_id': existing_page.get('current_revision_id')
                }
            
            # Check ETag and Last-Modified headers first
            etag = head_response.headers.get('ETag')
            last_modified = head_response.headers.get('Last-Modified')
            
            # Get current revision info
            current_revision = existing_page.get('current_revision')
            
            if etag or last_modified:
                if current_revision:
                    stored_etag = current_revision.get('metadata', {}).get('etag')
                    stored_last_modified = current_revision.get('metadata', {}).get('last_modified')
                    
                    # Debug logging
                    logger.debug(f"Header comparison for {url}:")
                    logger.debug(f"  Current ETag: {etag}")
                    logger.debug(f"  Stored ETag: {stored_etag}")
                    logger.debug(f"  Current Last-Modified: {last_modified}")
                    logger.debug(f"  Stored Last-Modified: {stored_last_modified}")
                    
                    # Check if headers have changed (only if both values exist and are different)
                    etag_changed = etag and stored_etag and etag != stored_etag
                    last_modified_changed = last_modified and stored_last_modified and last_modified != stored_last_modified
                    
                    # Also check if we have a new header that wasn't there before
                    etag_new = etag and not stored_etag
                    last_modified_new = last_modified and not stored_last_modified
                    
                    if etag_changed or last_modified_changed or etag_new or last_modified_new:
                        # Headers changed, but we need to check content hash to be sure
                        change_reason = []
                        if etag_changed:
                            change_reason.append(f"ETag: {stored_etag} -> {etag}")
                        if last_modified_changed:
                            change_reason.append(f"Last-Modified: {stored_last_modified} -> {last_modified}")
                        if etag_new:
                            change_reason.append(f"New ETag: {etag}")
                        if last_modified_new:
                            change_reason.append(f"New Last-Modified: {last_modified}")
                        
                        logger.info(f"Page {url} headers changed ({', '.join(change_reason)}), checking content hash...")
                        return self._check_content_hash_detailed(url, existing_page, current_revision)
                    else:
                        logger.debug(f"Page {url} headers unchanged, skipping content hash check")
                        return {
                            'has_changed': False,
                            'reason': 'Headers unchanged',
                            'old_revision_id': current_revision.get('id')
                        }
                else:
                    # No current revision but headers present - need to check content
                    logger.debug(f"Page {url} has headers but no current revision, checking content hash...")
                    return self._check_content_hash_detailed(url, existing_page, current_revision)
            
            # If no headers present, do a full fetch to check content hash
            logger.debug(f"Page {url} has no ETag or Last-Modified headers, checking content hash...")
            return self._check_content_hash_detailed(url, existing_page, current_revision)
            
        except Exception as e:
            logger.warning(f"Error checking page {url}: {e}")
            # If we can't check, assume it changed to be safe
            return {
                'has_changed': True,
                'reason': f'Error checking page: {str(e)}',
                'old_revision_id': existing_page.get('current_revision_id')
            }
    
    def _check_content_hash_detailed(self, url: str, existing_page: Dict, current_revision: Optional[Dict]) -> Dict[str, any]:
        """Check if page content has changed by comparing SHA256 hashes."""
        try:
            # Fetch full page
            response = self.session.get(url, timeout=15)
            if response.status_code != 200:
                return {
                    'has_changed': True,
                    'reason': f'HTTP {response.status_code} on full fetch',
                    'old_revision_id': current_revision.get('id') if current_revision else None
                }
            
            # Extract and normalize content
            content = self._extract_normalized_content(response.text)
            content_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
            
            # Debug logging
            logger.debug(f"Checking content hash for {url}")
            logger.debug(f"Current revision: {current_revision}")
            logger.debug(f"New content hash: {content_hash[:8]}...")
            
            # Check if we have a current revision
            if not current_revision:
                logger.info(f"No previous revision found for {url}, considering as changed")
                return {
                    'has_changed': True,
                    'reason': 'No previous revision found',
                    'old_revision_id': None
                }
            
            stored_hash = current_revision.get('content_sha256')
            if not stored_hash:
                logger.info(f"No stored hash for {url}, considering as changed")
                return {
                    'has_changed': True,
                    'reason': 'No stored content hash',
                    'old_revision_id': current_revision.get('id')
                }
            
            if content_hash != stored_hash:
                logger.info(f"Page {url} content hash changed: {stored_hash[:8]}... -> {content_hash[:8]}...")
                return {
                    'has_changed': True,
                    'reason': f'Content hash changed: {stored_hash[:8]}... -> {content_hash[:8]}...',
                    'old_revision_id': current_revision.get('id'),
                    'new_content_hash': content_hash
                }
            
            logger.info(f"Page {url} unchanged")
            return {
                'has_changed': False,
                'reason': 'No changes detected',
                'old_revision_id': current_revision.get('id')
            }
            
        except Exception as e:
            logger.warning(f"Error checking content hash for {url}: {e}")
            return {
                'has_changed': True,
                'reason': f'Error checking content hash: {str(e)}',
                'old_revision_id': current_revision.get('id') if current_revision else None
            }
    
    def _extract_normalized_content(self, html: str) -> str:
        """
        Extract and normalize content for hashing.
        Strips timestamps and other dynamic content that shouldn't affect change detection.
        """
        import re
        
        soup = BeautifulSoup(html, 'lxml')
        
        # Remove script and style tags
        for tag in soup(['script', 'style', 'noscript', 'iframe']):
            tag.decompose()
        
        # Remove elements that commonly contain dynamic content
        for selector in [
            '[class*="timestamp"]', '[class*="date"]', '[class*="time"]',
            '[id*="timestamp"]', '[id*="date"]', '[id*="time"]',
            '.timestamp', '.date', '.time', '.updated', '.modified',
            '[data-timestamp]', '[data-date]', '[data-time]'
        ]:
            for element in soup.select(selector):
                element.decompose()
        
        # Get text content
        text = soup.get_text()
        
        # Remove common timestamp patterns (more comprehensive)
        timestamp_patterns = [
            # ISO 8601 formats
            r'\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?',
            # Date formats
            r'\d{1,2}/\d{1,2}/\d{4}',
            r'\d{4}/\d{1,2}/\d{1,2}',
            r'\d{1,2}-\d{1,2}-\d{4}',
            # Time formats
            r'\d{1,2}:\d{2}:\d{2}(?:\.\d+)?',
            r'\d{1,2}:\d{2}(?::\d{2})?',
            # Relative time patterns
            r'\d+\s+(?:seconds?|minutes?|hours?|days?|weeks?|months?|years?)\s+ago',
            r'(?:just now|a moment ago|yesterday|today|tomorrow)',
            # Unix timestamps (10 digits)
            r'\b\d{10}\b',
            # Common date/time words
            r'(?:last updated|modified|created|published):\s*\d{4}-\d{2}-\d{2}',
            r'(?:last updated|modified|created|published):\s*\d{1,2}/\d{1,2}/\d{4}',
        ]
        
        for pattern in timestamp_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        # Remove common dynamic content patterns
        dynamic_patterns = [
            r'page\s+load\s+time:\s*[\d.]+ms',
            r'generated\s+at:\s*[\d\-\s:]+',
            r'last\s+modified:\s*[\d\-\s:]+',
            r'version:\s*[\d.]+',
            r'build\s+[\d.]+',
            r'revision\s+[\d.]+',
        ]
        
        for pattern in dynamic_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        # Remove excessive whitespace and normalize
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Remove very short words that might be artifacts
        words = text.split()
        words = [word for word in words if len(word) > 2 or word.isalpha()]
        
        return ' '.join(words)
    
    def _get_last_revision(self, page_id: str) -> Optional[Dict]:
        """Get the most recent revision for a page."""
        try:
            result = self.supabase.table("page_revisions").select("*").eq(
                "page_id", page_id
            ).order("created_at", desc=True).limit(1).execute()
            
            if result.data:
                return result.data[0]
            return None
        except Exception as e:
            logger.error(f"Failed to get last revision for page {page_id}: {e}")
            return None
    
    def _get_revision_by_id(self, revision_id: str) -> Optional[Dict]:
        """Get a specific revision by ID."""
        try:
            result = self.supabase.table("page_revisions").select("*").eq(
                "id", revision_id
            ).execute()
            
            if result.data and len(result.data) > 0:
                return result.data[0]
            return None
        except Exception as e:
            logger.error(f"Failed to get revision {revision_id}: {e}")
            return None
    
    def _get_page_info(self, url: str) -> Dict:
        """Get basic page info for a URL."""
        parsed = urlparse(url)
        return {
            'url': url,
            'path': parsed.path or '/',
            'canonical_url': url,
            'render_mode': 'STATIC',
            'is_indexable': True,
            'metadata': {}
        }
    
    def save_page_revision(self, page_id: str, content: str, title: str = "", 
                          description: str = "", metadata: Dict = None, 
                          old_revision_id: str = None) -> str:
        """Save a new page revision to the database and create diff record."""
        try:
            # Extract normalized content for hashing
            normalized_content = self._extract_normalized_content(content)
            content_hash = hashlib.sha256(normalized_content.encode('utf-8')).hexdigest()
            
            # Check if content hash has actually changed
            if old_revision_id:
                # Get the old revision to compare hashes
                old_revision = self._get_revision_by_id(old_revision_id)
                if old_revision and old_revision.get('content_sha256') == content_hash:
                    logger.info(f"Page {page_id} content hash unchanged ({content_hash[:8]}...), skipping revision creation")
                    
                    # Update page's last_seen_at but don't create new revision
                    self.supabase.table("pages").update({
                        'last_seen_at': datetime.utcnow().isoformat()
                    }).eq('id', page_id).execute()
                    
                    # Create diff record for UNCHANGED
                    self.db_utils.create_diff_record(
                        run_id=self.run_id,
                        page_id=page_id,
                        from_revision_id=old_revision_id,
                        to_revision_id=old_revision_id,  # Same revision
                        change_type="UNCHANGED",
                        summary="Content hash unchanged despite header changes"
                    )
                    
                    return old_revision_id  # Return existing revision ID
            
            # Extract additional metadata
            soup = BeautifulSoup(content, 'lxml')
            headings = [h.get_text(strip=True) for h in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])]
            
            # Count links
            internal_links = len([a for a in soup.find_all('a', href=True) 
                                if a.get('href') and not a.get('href').startswith(('http://', 'https://', 'mailto:', 'tel:'))])
            external_links = len([a for a in soup.find_all('a', href=True) 
                                if a.get('href') and a.get('href').startswith(('http://', 'https://'))])
            
            # Word count
            word_count = len(normalized_content.split())
            
            revision_data = {
                'page_id': page_id,
                'run_id': self.run_id,
                'content': content,
                'content_sha256': content_hash,
                'title': title,
                'meta_description': description,
                'canonical': None,  # Will be set if found
                'extracted_jsonld': None,  # Will be set if found
                'headings': headings,
                'internal_links': internal_links,
                'external_links': external_links,
                'word_count': word_count,
                'processed': True,
                'metadata': metadata or {}
            }
            
            result = self.supabase.table("page_revisions").insert(revision_data).execute()
            
            if result.data:
                revision_id = result.data[0]['id']
                logger.info(f"Saved page revision {revision_id} for page {page_id} with hash {content_hash[:8]}...")
                
                # Update page's current_revision_id
                self.supabase.table("pages").update({
                    'current_revision_id': revision_id,
                    'last_seen_at': datetime.utcnow().isoformat()
                }).eq('id', page_id).execute()
                
                # Create diff record if we have an old revision
                if old_revision_id:
                    self.db_utils.create_diff_record(
                        run_id=self.run_id,
                        page_id=page_id,
                        from_revision_id=old_revision_id,
                        to_revision_id=revision_id,
                        change_type="MODIFIED",
                        summary=f"Content updated - hash: {content_hash[:8]}..."
                    )
                else:
                    # This is a new page
                    self.db_utils.create_diff_record(
                        run_id=self.run_id,
                        page_id=page_id,
                        from_revision_id=None,
                        to_revision_id=revision_id,
                        change_type="CREATED",
                        summary="New page discovered"
                    )
                
                return revision_id
            else:
                logger.error(f"Failed to save page revision for {page_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error saving page revision for {page_id}: {e}")
            return None
    
    def mark_unchanged_pages(self, unchanged_pages: List[Dict]) -> None:
        """Mark unchanged pages in the current run."""
        try:
            unchanged_page_ids = [page['id'] for page in unchanged_pages if page.get('id')]
            if unchanged_page_ids:
                self.db_utils.mark_pages_as_unchanged(self.run_id, unchanged_page_ids)
                logger.info(f"Marked {len(unchanged_page_ids)} pages as unchanged")
        except Exception as e:
            logger.error(f"Error marking unchanged pages: {e}")
