# apps/worker/worker/crawler.py
"""Web crawler with change detection capabilities."""

import re
import time
import logging
from urllib.parse import urlparse, urljoin, urldefrag
from typing import Dict, List, Optional, Any

import requests
from bs4 import BeautifulSoup

from .change_detection import ChangeDetector
from .storage import get_supabase_client
from .constants import (
    DEFAULT_USER_AGENT,
    HTML_CONTENT_TYPES,
    DEFAULT_MAX_PAGES,
    DEFAULT_MAX_DEPTH,
    DEFAULT_CRAWL_DELAY,
    DEFAULT_TIMEOUT,
    TABLE_PAGES
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)  # Set appropriate log level


class Robots:
    """
    Minimal robots.txt parser using requests + urllib.robotparser-like interface.
    """

    def __init__(self, base_url: str, session: requests.Session, user_agent: str = DEFAULT_USER_AGENT):
        self.base_url = base_url
        self.session = session
        self.user_agent = user_agent
        self._allowed_cache = {}
        self._fetched = False
        self._rules_lines: List[str] = []

    def fetch(self):
        parsed = urlparse(self.base_url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        try:
            r = self.session.get(robots_url, timeout=10, headers={"User-Agent": self.user_agent})
            if r.status_code == 200:
                self._rules_lines = r.text.splitlines()
            else:
                self._rules_lines = []
        except Exception:
            self._rules_lines = []
        self._fetched = True

    def allows(self, path: str) -> bool:
        """
        Very simple interpretation: look for Disallow directives for User-agent: * and for our UA.
        If robots.txt absent or cannot be parsed, return True by default.
        This is conservative but practical for many sites.
        """
        if not self._fetched:
            self.fetch()

        ua = None
        allow = True
        rules_for_us: List[str] = []
        current_ua_groups: List[str] = []
        for raw in self._rules_lines:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split(":", 1)
            if len(parts) != 2:
                continue
            key, val = parts[0].strip().lower(), parts[1].strip()
            if key == "user-agent":
                ua = val
                current_ua_groups = [ua]
                continue
            if key in ("disallow", "allow"):
                p = val
                # choose if this rule applies
                if ua in ("*", self.user_agent) or ua == "*":
                    # collect rules only for the relevant user-agent group
                    rules_for_us.append((key, p))

        # apply Disallow rules: if any disallow prefix matches the path => disallowed
        # Note: a full robots parser is complex; this suffices for typical cases.
        for key, pattern in rules_for_us:
            if not pattern:
                # Disallow: <empty> means allow all
                if key == "disallow":
                    continue
            # normalize both
            if path.startswith(pattern):
                if key == "disallow":
                    return False
                if key == "allow":
                    return True
        return True


def normalize_url(base: str, link: str) -> Optional[str]:
    """
    Join relative URLs, strip fragments, normalize.
    Returns None for mailto:, tel:, javascript: or non-http schemes.
    """
    if not link:
        return None
    link = link.strip()
    if link.startswith("mailto:") or link.startswith("tel:") or link.startswith("javascript:"):
        return None
    joined = urljoin(base, link)
    joined, _ = urldefrag(joined)  # remove fragment
    parsed = urlparse(joined)
    if parsed.scheme not in ("http", "https"):
        return None
    return joined


def is_same_domain(seed: str, url: str) -> bool:
    return urlparse(seed).netloc == urlparse(url).netloc


def extract_text_and_meta(html: str, url: str) -> Dict[str, Any]:
    soup = BeautifulSoup(html, "lxml")
    title_tag = soup.find("title")
    title = title_tag.get_text(strip=True) if title_tag else ""
    # meta description
    meta_desc = ""
    md = soup.find("meta", attrs={"name": "description"})
    if md and md.get("content"):
        meta_desc = md.get("content").strip()
    # headings
    headings = [h.get_text(strip=True) for h in soup.find_all(re.compile("^h[1-6]$"))]
    # main text (simple)
    for s in soup(["script", "style", "noscript", "iframe"]):
        s.decompose()
    body = soup.body
    text = body.get_text(separator=" ", strip=True) if body else soup.get_text(separator=" ", strip=True)
    snippet = text[:400] + ("…" if len(text) > 400 else "")
    return {"title": title, "description": meta_desc, "headings": headings, "text_snippet": snippet, "full_text": text}


def _create_page_record(project_id: str, page_info: Dict) -> Optional[str]:
    """Create a new page record in the database."""
    try:
        from .storage import get_supabase_client
        from datetime import datetime
        
        supabase = get_supabase_client()
        
        page_data = {
            'project_id': project_id,
            'url': page_info['url'],
            'path': page_info.get('path', '/'),
            'canonical_url': page_info.get('canonical_url', page_info['url']),
            'render_mode': page_info.get('render_mode', 'STATIC'),
            'is_indexable': page_info.get('is_indexable', True),
            'discovered_at': datetime.utcnow().isoformat(),
            'metadata': page_info.get('metadata', {})
        }
        
        result = supabase.table(TABLE_PAGES).insert(page_data).execute()
        
        if result.data:
            page_id = result.data[0]['id']
            logger.info(f"Created new page record {page_id} for {page_info['url']}")
            return page_id
        else:
            logger.error(f"Failed to create page record for {page_info['url']}")
            return None
            
    except Exception as e:
        logger.error(f"Error creating page record for {page_info['url']}: {e}")
        return None


def crawl_with_change_detection(
    start_url: str,
    project_id: str,
    run_id: str,
    max_pages: int = DEFAULT_MAX_PAGES,
    max_depth: int = DEFAULT_MAX_DEPTH,
    delay: float = DEFAULT_CRAWL_DELAY,
    session: Optional[requests.Session] = None,
    user_agent: str = DEFAULT_USER_AGENT,
) -> Dict[str, Any]:
    """
    Crawl with change detection integration.
    Only crawls pages that have changed or are new.
    """
    if session is None:
        session = requests.Session()
    session.headers.update({"User-Agent": user_agent})

    # Initialize change detector
    change_detector = ChangeDetector(project_id, run_id)
    
    # Detect changes first
    changes = change_detector.detect_changes(start_url)
    
    if not changes['has_changes']:
        logger.info("No changes detected, skipping crawl")
        return {
            "start_url": start_url,
            "pages_crawled": 0,
            "max_pages": max_pages,
            "max_depth": max_depth,
            "pages": [],
            "changes_detected": False,
            "changed_pages": [],
            "new_pages": [],
            "unchanged_pages": changes['unchanged_pages']
        }
    
    logger.info(f"Changes detected: {len(changes['changed_pages'])} changed, "
               f"{len(changes['new_pages'])} new pages")
    
    # Crawl only changed and new pages
    pages_to_crawl = changes['changed_pages'] + changes['new_pages']
    crawled_pages = []
    
    for page_info in pages_to_crawl[:max_pages]:
        url = page_info['url']
        logger.info(f"Crawling changed/new page: {url}")
        
        try:
            # Fetch page
            r = session.get(url, timeout=DEFAULT_TIMEOUT)
            if r.status_code != 200:
                logger.warning(f"Failed to fetch {url}: {r.status_code}")
                continue
            
            # Extract metadata
            data = extract_text_and_meta(r.text, url)
            
            # Handle page creation/update
            page_id = page_info.get('id')
            old_revision_id = page_info.get('old_revision_id')
            
            if not page_id:
                # This is a new page, we need to create it first
                page_id = _create_page_record(project_id, page_info)
                old_revision_id = None  # New page has no old revision
            
            if page_id:
                # Save revision with full content and diff tracking
                revision_id = change_detector.save_page_revision(
                    page_id=page_id,
                    content=r.text,
                    title=data["title"],
                    description=data["description"],
                    metadata={
                        "status_code": r.status_code,
                        "etag": r.headers.get('ETag'),
                        "last_modified": r.headers.get('Last-Modified'),
                        "content_type": r.headers.get('Content-Type'),
                        "content_length": r.headers.get('Content-Length'),
                        "change_reason": page_info.get('change_reason', 'Unknown')
                    },
                    old_revision_id=old_revision_id
                )
                
                if revision_id:
                    # Add to crawled pages for result
                    crawled_pages.append({
                        "url": url,
                        "status_code": r.status_code,
                        "title": data["title"],
                        "description": data["description"],
                        "headings": data["headings"],
                        "snippet": data["text_snippet"],
                        "page_id": page_id,
                        "revision_id": revision_id,
                        "change_reason": page_info.get('change_reason', 'Unknown')
                    })
            
            # Rate limiting
            time.sleep(delay)
            
        except Exception as e:
            logger.warning(f"Error crawling {url}: {e}")
            continue
    
    result = {
        "start_url": start_url,
        "pages_crawled": len(crawled_pages),
        "max_pages": max_pages,
        "max_depth": max_depth,
        "pages": crawled_pages,
        "changes_detected": True,
        "changed_pages": changes['changed_pages'],
        "new_pages": changes['new_pages'],
        "unchanged_pages": changes['unchanged_pages']
    }
    
    return result


