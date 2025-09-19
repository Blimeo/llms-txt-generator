"""Unit tests for crawler business logic."""

import pytest
from unittest.mock import Mock, patch, MagicMock
import requests

from worker.crawler import (
    crawl_with_change_detection,
    _create_page_record,
    normalize_url,
    is_same_domain,
    extract_text_and_meta,
    Robots
)


class TestCrawlerBusinessLogic:
    """Test cases for crawler business logic."""

    def test_normalize_url_valid_urls(self):
        """Test URL normalization with valid URLs."""
        # Test absolute URLs
        assert normalize_url("https://example.com", "https://example.com/page") == "https://example.com/page"
        assert normalize_url("https://example.com", "http://example.com/page") == "http://example.com/page"
        
        # Test relative URLs
        assert normalize_url("https://example.com", "/page") == "https://example.com/page"
        assert normalize_url("https://example.com", "page") == "https://example.com/page"
        assert normalize_url("https://example.com/", "page") == "https://example.com/page"
        
        # Test URLs with fragments
        assert normalize_url("https://example.com", "/page#section") == "https://example.com/page"
        
        # Test URLs with query parameters
        assert normalize_url("https://example.com", "/page?param=value") == "https://example.com/page?param=value"

    def test_normalize_url_invalid_urls(self):
        """Test URL normalization with invalid URLs."""
        # Test non-HTTP schemes
        assert normalize_url("https://example.com", "mailto:test@example.com") is None
        assert normalize_url("https://example.com", "tel:+1234567890") is None
        assert normalize_url("https://example.com", "javascript:alert('test')") is None
        assert normalize_url("https://example.com", "ftp://example.com") is None
        
        # Test empty or None URLs
        assert normalize_url("https://example.com", "") is None
        assert normalize_url("https://example.com", None) is None

    def test_is_same_domain(self):
        """Test domain comparison logic."""
        # Same domains
        assert is_same_domain("https://example.com", "https://example.com/page") is True
        assert is_same_domain("https://example.com", "http://example.com/page") is True
        assert is_same_domain("https://example.com", "https://example.com:8080/page") is True
        
        # Different domains
        assert is_same_domain("https://example.com", "https://other.com") is False
        assert is_same_domain("https://example.com", "https://subdomain.example.com") is False

    def test_extract_text_and_meta(self):
        """Test HTML text and metadata extraction."""
        html = """
        <html>
        <head>
            <title>Test Page</title>
            <meta name="description" content="This is a test page">
        </head>
        <body>
            <h1>Main Content</h1>
            <p>Some content here</p>
        </body>
        </html>
        """
        
        result = extract_text_and_meta(html, "https://example.com")
        
        assert result["title"] == "Test Page"
        assert result["description"] == "This is a test page"

    def test_extract_text_and_meta_missing_elements(self):
        """Test HTML extraction with missing title and description."""
        html = """
        <html>
        <head>
        </head>
        <body>
            <h1>Main Content</h1>
        </body>
        </html>
        """
        
        result = extract_text_and_meta(html, "https://example.com")
        
        assert result["title"] == ""
        assert result["description"] == ""

    def test_extract_text_and_meta_empty_content(self):
        """Test HTML extraction with empty content."""
        html = ""
        
        result = extract_text_and_meta(html, "https://example.com")
        
        assert result["title"] == ""
        assert result["description"] == ""

    def test_create_page_record_success(self, mock_data_fetcher):
        """Test successful page record creation."""
        page_info = {
            "url": "https://example.com",
            "path": "/",
            "canonical_url": "https://example.com",
            "render_mode": "STATIC",
            "is_indexable": True,
            "metadata": {"test": "value"}
        }
        
        result = _create_page_record(mock_data_fetcher, "project_123", page_info)
        
        assert result == "page_123"
        mock_data_fetcher.create_page_record.assert_called_once_with("project_123", page_info)

    def test_create_page_record_failure(self, mock_data_fetcher):
        """Test page record creation failure."""
        mock_data_fetcher.create_page_record.return_value = None
        
        page_info = {"url": "https://example.com"}
        
        result = _create_page_record(mock_data_fetcher, "project_123", page_info)
        
        assert result is None

    @patch('worker.crawler.ChangeDetector')
    def test_crawl_with_change_detection_no_changes(self, mock_change_detector_class, mock_data_fetcher):
        """Test crawl when no changes are detected."""
        # Mock change detector
        mock_detector = Mock()
        mock_detector.detect_changes.return_value = {
            "has_changes": False,
            "changed_pages": [],
            "new_pages": [],
            "unchanged_pages": [
                {"id": "page_123", "url": "https://example.com"}
            ]
        }
        mock_change_detector_class.return_value = mock_detector
        
        result = crawl_with_change_detection(
            start_url="https://example.com",
            project_id="project_123",
            run_id="run_456",
            data_fetcher=mock_data_fetcher,
            max_pages=10,
            max_depth=2,
            delay=0.5
        )
        
        assert result["changes_detected"] is False
        assert result["pages_crawled"] == 0
        assert result["pages"] == []
        assert result["unchanged_pages"] == [{"id": "page_123", "url": "https://example.com"}]

    @patch('worker.crawler.ChangeDetector')
    @patch('worker.crawler.requests.Session')
    def test_crawl_with_change_detection_with_changes(self, mock_session_class, mock_change_detector_class, mock_data_fetcher):
        """Test crawl when changes are detected."""
        # Mock change detector
        mock_detector = Mock()
        mock_detector.detect_changes.return_value = {
            "has_changes": True,
            "changed_pages": [
                {
                    "id": "page_123",
                    "url": "https://example.com",
                    "change_reason": "Content hash changed",
                    "old_revision_id": "revision_456"
                }
            ],
            "new_pages": [
                {
                    "url": "https://example.com/about",
                    "path": "/about",
                    "canonical_url": "https://example.com/about",
                    "render_mode": "STATIC",
                    "is_indexable": True,
                    "metadata": {}
                }
            ],
            "unchanged_pages": []
        }
        
        # Mock page revision saving
        mock_detector.save_page_revision.return_value = "revision_789"
        mock_change_detector_class.return_value = mock_detector
        
        # Mock session and response
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "<html><title>Test Page</title><meta name='description' content='Test description'></html>"
        mock_session.get.return_value = mock_response
        mock_session_class.return_value = mock_session
        
        result = crawl_with_change_detection(
            start_url="https://example.com",
            project_id="project_123",
            run_id="run_456",
            data_fetcher=mock_data_fetcher,
            max_pages=10,
            max_depth=2,
            delay=0.5
        )
        
        assert result["changes_detected"] is True
        assert result["pages_crawled"] == 2  # 1 changed + 1 new
        assert len(result["pages"]) == 2
        assert result["changed_pages"] == [{"id": "page_123", "url": "https://example.com", "change_reason": "Content hash changed", "old_revision_id": "revision_456"}]
        assert result["new_pages"] == [{"url": "https://example.com/about", "path": "/about", "canonical_url": "https://example.com/about", "render_mode": "STATIC", "is_indexable": True, "metadata": {}}]

    @patch('worker.crawler.ChangeDetector')
    @patch('worker.crawler.requests.Session')
    def test_crawl_with_change_detection_http_error(self, mock_session_class, mock_change_detector_class, mock_data_fetcher):
        """Test crawl when HTTP request fails."""
        # Mock change detector
        mock_detector = Mock()
        mock_detector.detect_changes.return_value = {
            "has_changes": True,
            "changed_pages": [
                {
                    "id": "page_123",
                    "url": "https://example.com",
                    "change_reason": "Content hash changed"
                }
            ],
            "new_pages": [],
            "unchanged_pages": []
        }
        mock_change_detector_class.return_value = mock_detector
        
        # Mock session with HTTP error
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 404
        mock_session.get.return_value = mock_response
        mock_session_class.return_value = mock_session
        
        result = crawl_with_change_detection(
            start_url="https://example.com",
            project_id="project_123",
            run_id="run_456",
            data_fetcher=mock_data_fetcher,
            max_pages=10,
            max_depth=2,
            delay=0.5
        )
        
        assert result["changes_detected"] is True
        assert result["pages_crawled"] == 0  # No pages crawled due to HTTP error
        assert result["pages"] == []

    @patch('worker.crawler.ChangeDetector')
    @patch('worker.crawler.requests.Session')
    def test_crawl_with_change_detection_new_page_creation(self, mock_session_class, mock_change_detector_class, mock_data_fetcher):
        """Test crawl with new page creation."""
        # Mock change detector
        mock_detector = Mock()
        mock_detector.detect_changes.return_value = {
            "has_changes": True,
            "changed_pages": [],
            "new_pages": [
                {
                    "url": "https://example.com/new",
                    "path": "/new",
                    "canonical_url": "https://example.com/new",
                    "render_mode": "STATIC",
                    "is_indexable": True,
                    "metadata": {}
                }
            ],
            "unchanged_pages": []
        }
        
        # Mock page revision saving
        mock_detector.save_page_revision.return_value = "revision_789"
        mock_change_detector_class.return_value = mock_detector
        
        # Mock session and response
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "<html><title>New Page</title></html>"
        mock_session.get.return_value = mock_response
        mock_session_class.return_value = mock_session
        
        result = crawl_with_change_detection(
            start_url="https://example.com",
            project_id="project_123",
            run_id="run_456",
            data_fetcher=mock_data_fetcher,
            max_pages=10,
            max_depth=2,
            delay=0.5
        )
        
        # Verify that create_page_record was called for the new page
        mock_data_fetcher.create_page_record.assert_called_once()
        
        # Verify that save_page_revision was called
        mock_detector.save_page_revision.assert_called_once()

    @patch('worker.crawler.ChangeDetector')
    def test_crawl_with_change_detection_max_pages_limit(self, mock_change_detector_class, mock_data_fetcher):
        """Test crawl respects max_pages limit."""
        # Mock change detector with many pages
        mock_detector = Mock()
        mock_detector.detect_changes.return_value = {
            "has_changes": True,
            "changed_pages": [
                {"id": f"page_{i}", "url": f"https://example.com/page{i}"}
                for i in range(15)  # More than max_pages
            ],
            "new_pages": [],
            "unchanged_pages": []
        }
        mock_detector.save_page_revision.return_value = "revision_789"
        mock_change_detector_class.return_value = mock_detector
        
        result = crawl_with_change_detection(
            start_url="https://example.com",
            project_id="project_123",
            run_id="run_456",
            data_fetcher=mock_data_fetcher,
            max_pages=10,  # Limit to 10 pages
            max_depth=2,
            delay=0.5
        )
        
        # Should only process max_pages number of pages
        assert result["pages_crawled"] <= 10
        assert result["max_pages"] == 10

    def test_crawl_with_change_detection_custom_session(self, mock_data_fetcher):
        """Test crawl with custom session provided."""
        custom_session = Mock()
        custom_session.headers = {}
        
        with patch('worker.crawler.ChangeDetector') as mock_change_detector_class:
            mock_detector = Mock()
            mock_detector.detect_changes.return_value = {
                "has_changes": False,
                "changed_pages": [],
                "new_pages": [],
                "unchanged_pages": []
            }
            mock_change_detector_class.return_value = mock_detector
            
            result = crawl_with_change_detection(
                start_url="https://example.com",
                project_id="project_123",
                run_id="run_456",
                data_fetcher=mock_data_fetcher,
                session=custom_session
            )
            
            # Verify custom session was used
            assert result["changes_detected"] is False

    def test_crawl_with_change_detection_custom_user_agent(self, mock_data_fetcher):
        """Test crawl with custom user agent."""
        with patch('worker.crawler.ChangeDetector') as mock_change_detector_class, \
             patch('worker.crawler.requests.Session') as mock_session_class:
            
            mock_detector = Mock()
            mock_detector.detect_changes.return_value = {
                "has_changes": False,
                "changed_pages": [],
                "new_pages": [],
                "unchanged_pages": []
            }
            mock_change_detector_class.return_value = mock_detector
            
            mock_session = Mock()
            mock_session_class.return_value = mock_session
            
            result = crawl_with_change_detection(
                start_url="https://example.com",
                project_id="project_123",
                run_id="run_456",
                data_fetcher=mock_data_fetcher,
                user_agent="CustomBot/1.0"
            )
            
            # Verify custom user agent was set
            mock_session.headers.update.assert_called_with({"User-Agent": "CustomBot/1.0"})


class TestRobots:
    """Test cases for Robots class."""

    def test_robots_init(self):
        """Test Robots class initialization."""
        session = Mock()
        robots = Robots("https://example.com", session, "TestBot/1.0")
        
        assert robots.base_url == "https://example.com"
        assert robots.session == session
        assert robots.user_agent == "TestBot/1.0"
        assert robots._fetched is False

    def test_robots_fetch_success(self):
        """Test successful robots.txt fetch."""
        session = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "User-agent: *\nDisallow: /admin/\nAllow: /"
        session.get.return_value = mock_response
        
        robots = Robots("https://example.com", session, "TestBot/1.0")
        robots.fetch()
        
        assert robots._fetched is True
        assert "User-agent: *" in robots._rules_lines
        assert "Disallow: /admin/" in robots._rules_lines

    @patch('worker.crawler.requests.Session.get')
    def test_robots_fetch_failure(self, mock_get):
        """Test robots.txt fetch failure."""
        session = Mock()
        mock_get.side_effect = Exception("Network error")
        
        robots = Robots("https://example.com", session, "TestBot/1.0")
        robots.fetch()
        
        assert robots._fetched is True
        assert robots._rules_lines == []

    def test_robots_allows_simple_rules(self):
        """Test robots.txt allows method with simple rules."""
        session = Mock()
        robots = Robots("https://example.com", session, "TestBot/1.0")
        robots._fetched = True
        robots._rules_lines = [
            "User-agent: *",
            "Disallow: /admin/",
            "Allow: /public/"
        ]
        
        # Test allowed paths
        assert robots.allows("/") is True
        assert robots.allows("/public/") is True
        assert robots.allows("/public/page.html") is True
        
        # Test disallowed paths
        assert robots.allows("/admin/") is False
        assert robots.allows("/admin/users") is False

    def test_robots_allows_empty_disallow(self):
        """Test robots.txt with empty Disallow (which means allow all)."""
        session = Mock()
        robots = Robots("https://example.com", session, "TestBot/1.0")
        robots._fetched = True
        robots._rules_lines = [
            "User-agent: *",
            "Disallow:"
        ]
        
        # Empty Disallow should allow all
        assert robots.allows("/") is True
        assert robots.allows("/admin/") is True
        assert robots.allows("/any/path") is True

    def test_robots_allows_no_rules(self):
        """Test robots.txt with no rules (default allow)."""
        session = Mock()
        robots = Robots("https://example.com", session, "TestBot/1.0")
        robots._fetched = True
        robots._rules_lines = []
        
        # No rules should default to allow
        assert robots.allows("/") is True
        assert robots.allows("/admin/") is True
