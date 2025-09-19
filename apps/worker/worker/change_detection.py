# apps/worker/worker/change_detection.py
"""Change detection for web pages using headers and content hashing."""

import hashlib
import logging
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse
import xml.etree.ElementTree as ET

import requests
from bs4 import BeautifulSoup

from .data_fetcher import DataFetcher
from .constants import (
    DEFAULT_USER_AGENT,
    HEAD_TIMEOUT,
    DEFAULT_TIMEOUT,
    SITEMAP_NAMESPACE
)

logger = logging.getLogger(__name__)


class ChangeDetector:
    """
    1. Sitemap + Headers first: If site has sitemap.xml, fetch and use LastMod / URLs; 
       request HEAD for ETag/Last-Modified; if unchanged, skip heavy fetch.
    2. Hash-based diff: For fetched HTML (post-render if needed), compute SHA256 of the 
       normalized important content (strip timestamp-like content). Save hash in DB; 
       if changed — enqueue generation via Cloud Tasks for Python workers to process.
    """
    
    def __init__(self, project_id: str, run_id: str, data_fetcher: DataFetcher):
        self.project_id = project_id
        self.run_id = run_id
        self.data_fetcher = data_fetcher
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": DEFAULT_USER_AGENT
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
        existing_pages = self.data_fetcher.get_existing_pages_with_revisions(self.project_id)
        existing_urls = {page['url'] for page in existing_pages}
        logger.info(f"Found {len(existing_pages)} existing pages in database")
        
        # Step 2: Hash-based diff for fetched HTML content
        # Batch process all URLs to minimize DB calls
        all_urls = set(sitemap_urls) | existing_urls | {base_url}
        logger.info(f"Processing {len(all_urls)} URLs total (sitemap: {len(sitemap_urls)}, existing: {len(existing_urls)}, base_url included)")
        
        # Process all URLs in batches for efficiency
        changed_pages = []
        unchanged_pages = []
        new_pages = []
        
        # Process URLs in batches
        from .constants import DEFAULT_BATCH_SIZE
        batch_size = DEFAULT_BATCH_SIZE
        url_list = list(all_urls)
        
        for i in range(0, len(url_list), batch_size):
            batch_urls = url_list[i:i + batch_size]
            logger.info(f"Processing batch {i//batch_size + 1}/{(len(url_list) + batch_size - 1)//batch_size}")
            
            batch_results = self._process_url_batch(batch_urls, existing_pages, sitemap_urls)
            changed_pages.extend(batch_results['changed'])
            unchanged_pages.extend(batch_results['unchanged'])
            new_pages.extend(batch_results['new'])
                
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
        
        return result
    
    def _fetch_sitemap_urls(self, base_url: str) -> List[str]:
        """Fetch URLs from sitemap.xml if available."""
        parsed = urlparse(base_url)
        sitemap_url = f"{parsed.scheme}://{parsed.netloc}/sitemap.xml"
        
        try:
            response = self.session.get(sitemap_url, timeout=HEAD_TIMEOUT)
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
            sitemap_ns = f"{{{SITEMAP_NAMESPACE}}}"
            if root.tag.endswith('sitemapindex'):
                # This is a sitemap index, get individual sitemaps
                for sitemap in root.findall(f'.//{sitemap_ns}sitemap'):
                    loc = sitemap.find(f'{sitemap_ns}loc')
                    if loc is not None:
                        # Fetch individual sitemap
                        try:
                            sub_response = self.session.get(loc.text, timeout=HEAD_TIMEOUT)
                            if sub_response.status_code == 200:
                                urls.extend(self._parse_sitemap(sub_response.text))
                        except Exception as e:
                            logger.warning(f"Failed to fetch sub-sitemap {loc.text}: {e}")
            else:
                # Regular sitemap
                for url in root.findall(f'.//{sitemap_ns}url'):
                    loc = url.find(f'{sitemap_ns}loc')
                    if loc is not None:
                        # Normalize URL to ensure consistent comparison with existing pages
                        normalized_url = self._normalize_url(loc.text)
                        urls.append(normalized_url)
        except ET.ParseError as e:
            logger.warning(f"Failed to parse sitemap XML: {e}")
        
        return urls
    
    def _normalize_url(self, url: str) -> str:
        """Normalize URL to ensure consistent comparison."""
        if not url:
            return url
        
        # Ensure URL has a scheme - if missing, add https://
        if not url.startswith(('http://', 'https://')):
            logger.debug(f"URL missing scheme, adding https://: {url}")
            url = f"https://{url}"
        
        return url
    
    
    def _process_url_batch(self, urls: List[str], existing_pages: List[Dict], sitemap_urls: List[str]) -> Dict[str, List[Dict]]:
        """Process a batch of URLs for change detection."""
        changed_pages = []
        unchanged_pages = []
        new_pages = []
        
        # Create lookup for existing pages
        existing_pages_by_url = {page['url']: page for page in existing_pages}
        
        logger.debug(f"Processing {len(urls)} URLs against {len(existing_pages_by_url)} existing pages")
        logger.debug(f"Existing page URLs: {list(existing_pages_by_url.keys())[:5]}...")  # Show first 5 for debugging
        
        for url in urls:
            try:
                if url in existing_pages_by_url:
                    # Existing page - check for changes
                    existing_page = existing_pages_by_url[url]
                    logger.debug(f"Found existing page for URL: {url}")
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
                    logger.debug(f"Treating as new page: {url}")
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
        Check if a page has changed by comparing content hashes.
        Simplified approach - just check content hash directly.
        """
        try:
            # Get current revision info
            current_revision = existing_page.get('current_revision')
            
            # Always check content hash for simplicity
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
            response = self.session.get(url, timeout=DEFAULT_TIMEOUT)
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
            logger.debug(f"Checking content hash for {url}: {content_hash[:8]}...")
            
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
        Simplified approach - just remove scripts/styles and normalize whitespace.
        """
        soup = BeautifulSoup(html, 'lxml')
        
        # Remove script and style tags
        for tag in soup(['script', 'style', 'noscript', 'iframe']):
            tag.decompose()
        
        # Get text content
        text = soup.get_text()
        
        # Remove excessive whitespace and normalize
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    
    def _get_page_info(self, url: str) -> Dict:
        """Get basic page info for a URL."""
        # Normalize URL to ensure consistent comparison
        url = self._normalize_url(url)
        
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
        """Save a new page revision to the database."""
        try:
            # Extract normalized content for hashing
            normalized_content = self._extract_normalized_content(content)
            content_hash = hashlib.sha256(normalized_content.encode('utf-8')).hexdigest()
            
            # Check if content hash has actually changed
            if old_revision_id:
                # Get the old revision to compare hashes
                old_revision = self.data_fetcher.get_revision_by_id(old_revision_id)
                if old_revision and old_revision.get('content_sha256') == content_hash:
                    logger.info(f"Page {page_id} content hash unchanged ({content_hash[:8]}...), skipping revision creation")
                    
                    # Update page's last_seen_at but don't create new revision
                    self.data_fetcher.update_page_last_seen(page_id)
                    
                    return old_revision_id  # Return existing revision ID
            
            # Create revision data with minimal metadata
            revision_id = self.data_fetcher.create_page_revision(
                page_id=page_id,
                run_id=self.run_id,
                content=content,
                content_hash=content_hash,
                title=title,
                description=description,
                metadata=metadata or {}
            )
            
            if revision_id:
                logger.info(f"Saved page revision {revision_id} for page {page_id} with hash {content_hash[:8]}...")
                
                # Update page's current_revision_id
                self.data_fetcher.update_page_revision(page_id, revision_id)
                      
                return revision_id
            else:
                logger.error(f"Failed to save page revision for {page_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error saving page revision for {page_id}: {e}")
            return None
