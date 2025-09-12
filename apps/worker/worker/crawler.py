# apps/worker/worker/crawler.py
import time
import re
import logging
from urllib.parse import urlparse, urljoin, urldefrag
from collections import deque
import requests
from bs4 import BeautifulSoup
from typing import Dict, Set, List, Optional, Any

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

DEFAULT_USER_AGENT = "llms-txt-crawler/1.0 (+https://example.com)"
HTML_CONTENT_TYPES = {"text/html", "application/xhtml+xml"}


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


def crawl(
    start_url: str,
    max_pages: int = 200,
    max_depth: int = 2,
    delay: float = 0.5,
    session: Optional[requests.Session] = None,
    user_agent: str = DEFAULT_USER_AGENT,
) -> Dict[str, Any]:
    """
    BFS crawl starting from start_url. Returns a dict with metadata and list of pages.
    - respects same-domain by default
    - respects robots.txt (best-effort)
    - rate-limits by sleeping `delay` seconds between requests to the same domain
    """
    if session is None:
        session = requests.Session()
    session.headers.update({"User-Agent": user_agent})

    parsed = urlparse(start_url)
    base_domain = f"{parsed.scheme}://{parsed.netloc}"
    robots = Robots(base_domain, session, user_agent=user_agent)

    visited: Set[str] = set()
    pages: List[Dict[str, Any]] = []
    q = deque()
    q.append((start_url, 0))

    last_request_time_by_host: Dict[str, float] = {}

    while q and len(pages) < max_pages:
        url, depth = q.popleft()
        if url in visited:
            continue
        if depth > max_depth:
            continue
        visited.add(url)

        # check robots
        path = urlparse(url).path or "/"
        try:
            if not robots.allows(path):
                logger.info("robots.txt disallows %s", url)
                continue
        except Exception:
            # if robots parsing fails, be permissive
            pass

        # respect rate limit per host
        host = urlparse(url).netloc
        last = last_request_time_by_host.get(host, 0)
        since = time.time() - last
        if since < delay:
            to_wait = delay - since
            time.sleep(to_wait)

        # fetch
        logger.info("fetching %s (depth=%s)", url, depth)
        try:
            r = session.get(url, timeout=15)
            last_request_time_by_host[host] = time.time()
        except Exception as e:
            logger.warning("failed to fetch %s: %s", url, e)
            continue

        # check content-type
        ctype = r.headers.get("Content-Type", "")
        if not any(ct in ctype for ct in HTML_CONTENT_TYPES):
            logger.info("skipping non-html %s (%s)", url, ctype)
            continue

        try:
            data = extract_text_and_meta(r.text, url)
        except Exception:
            data = {"title": "", "description": "", "headings": [], "text_snippet": "", "full_text": ""}

        # record page
        pages.append(
            {
                "url": url,
                "status_code": r.status_code,
                "title": data["title"],
                "description": data["description"],
                "headings": data["headings"],
                "snippet": data["text_snippet"],
            }
        )

        # discover links (same-domain)
        soup = BeautifulSoup(r.text, "lxml")
        for a in soup.find_all("a", href=True):
            normalized = normalize_url(url, a["href"])
            if not normalized:
                continue
            if not is_same_domain(start_url, normalized):
                continue
            if normalized in visited:
                continue
            q.append((normalized, depth + 1))

    result = {
        "start_url": start_url,
        "pages_crawled": len(pages),
        "max_pages": max_pages,
        "max_depth": max_depth,
        "pages": pages,
    }
    return result
