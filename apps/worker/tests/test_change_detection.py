"""Unit tests for change detection business logic."""

import pytest
from unittest.mock import Mock, patch, MagicMock
import hashlib

from worker.change_detection import ChangeDetector


class TestChangeDetector:
    """Test cases for ChangeDetector class."""

    def test_init(self, mock_data_fetcher):
        """Test ChangeDetector initialization."""
        detector = ChangeDetector("project_123", "run_456", mock_data_fetcher)
        
        assert detector.project_id == "project_123"
        assert detector.run_id == "run_456"
        assert detector.data_fetcher == mock_data_fetcher
        assert detector.session is not None
        assert "User-Agent" in detector.session.headers

    @patch('worker.change_detection.requests.Session.get')
    def test_detect_changes_no_sitemap(self, mock_get, mock_data_fetcher):
        """Test change detection when no sitemap is available."""
        # Mock sitemap fetch failure
        mock_get.side_effect = Exception("Sitemap not found")
        
        # Mock existing pages
        mock_data_fetcher.get_existing_pages_with_revisions.return_value = [
            {
                "id": "page_123",
                "url": "https://example.com",
                "current_revision": {
                    "id": "revision_456",
                    "content_sha256": "abc123"
                }
            }
        ]
        
        detector = ChangeDetector("project_123", "run_456", mock_data_fetcher)
        
        with patch.object(detector, '_process_url_batch') as mock_process:
            mock_process.return_value = {
                'changed': [],
                'unchanged': [{"id": "page_123", "url": "https://example.com"}],
                'new': []
            }
            
            result = detector.detect_changes("https://example.com")
            
            assert result["has_changes"] is False
            assert result["changed_pages"] == []
            assert result["new_pages"] == []
            assert len(result["unchanged_pages"]) == 1

    @patch('worker.change_detection.requests.Session.get')
    def test_detect_changes_with_sitemap(self, mock_get, mock_data_fetcher):
        """Test change detection with sitemap available."""
        # Mock sitemap response
        sitemap_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
            <url>
                <loc>https://example.com</loc>
            </url>
            <url>
                <loc>https://example.com/about</loc>
            </url>
        </urlset>"""
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = sitemap_xml
        mock_get.return_value = mock_response
        
        # Mock existing pages
        mock_data_fetcher.get_existing_pages_with_revisions.return_value = [
            {
                "id": "page_123",
                "url": "https://example.com",
                "current_revision": {
                    "id": "revision_456",
                    "content_sha256": "abc123"
                }
            }
        ]
        
        detector = ChangeDetector("project_123", "run_456", mock_data_fetcher)
        
        with patch.object(detector, '_process_url_batch') as mock_process:
            mock_process.return_value = {
                'changed': [],
                'unchanged': [{"id": "page_123", "url": "https://example.com"}],
                'new': [{"url": "https://example.com/about"}]
            }
            
            result = detector.detect_changes("https://example.com")
            
            assert result["has_changes"] is True
            assert result["new_pages"] == [{"url": "https://example.com/about"}]

    def test_fetch_sitemap_urls_success(self, mock_data_fetcher):
        """Test successful sitemap URL fetching."""
        detector = ChangeDetector("project_123", "run_456", mock_data_fetcher)
        
        sitemap_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
            <url>
                <loc>https://example.com</loc>
            </url>
            <url>
                <loc>https://example.com/about</loc>
            </url>
            <url>
                <loc>https://example.com/contact</loc>
            </url>
        </urlset>"""
        
        with patch.object(detector.session, 'get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.text = sitemap_xml
            mock_get.return_value = mock_response
            
            urls = detector._fetch_sitemap_urls("https://example.com")
            
            assert len(urls) == 3
            assert "https://example.com" in urls
            assert "https://example.com/about" in urls
            assert "https://example.com/contact" in urls

    def test_fetch_sitemap_urls_sitemap_index(self, mock_data_fetcher):
        """Test sitemap index parsing."""
        detector = ChangeDetector("project_123", "run_456", mock_data_fetcher)
        
        sitemap_index_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
            <sitemap>
                <loc>https://example.com/sitemap1.xml</loc>
            </sitemap>
            <sitemap>
                <loc>https://example.com/sitemap2.xml</loc>
            </sitemap>
        </sitemapindex>"""
        
        sub_sitemap_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
            <url>
                <loc>https://example.com/page1</loc>
            </url>
        </urlset>"""
        
        with patch.object(detector.session, 'get') as mock_get:
            # First call returns sitemap index
            mock_response1 = Mock()
            mock_response1.status_code = 200
            mock_response1.text = sitemap_index_xml
            
            # Subsequent calls return sub-sitemaps
            mock_response2 = Mock()
            mock_response2.status_code = 200
            mock_response2.text = sub_sitemap_xml
            
            mock_get.side_effect = [mock_response1, mock_response2, mock_response2]
            
            urls = detector._fetch_sitemap_urls("https://example.com")
            
            # Should have URLs from both sub-sitemaps
            assert len(urls) == 2
            assert "https://example.com/page1" in urls

    def test_normalize_url(self, mock_data_fetcher):
        """Test URL normalization."""
        detector = ChangeDetector("project_123", "run_456", mock_data_fetcher)
        
        # Test URLs with schemes
        assert detector._normalize_url("https://example.com") == "https://example.com"
        assert detector._normalize_url("http://example.com") == "http://example.com"
        
        # Test URLs without schemes
        assert detector._normalize_url("example.com") == "https://example.com"
        assert detector._normalize_url("subdomain.example.com") == "https://subdomain.example.com"
        
        # Test empty URL
        assert detector._normalize_url("") == ""
        assert detector._normalize_url(None) is None

    def test_process_url_batch_existing_pages(self, mock_data_fetcher):
        """Test processing URL batch with existing pages."""
        detector = ChangeDetector("project_123", "run_456", mock_data_fetcher)
        
        existing_pages = [
            {
                "id": "page_123",
                "url": "https://example.com",
                "current_revision": {
                    "id": "revision_456",
                    "content_sha256": "abc123"
                }
            }
        ]
        
        urls = ["https://example.com", "https://example.com/new"]
        sitemap_urls = ["https://example.com", "https://example.com/new"]
        
        with patch.object(detector, '_check_page_changes') as mock_check:
            mock_check.return_value = {
                'has_changed': False,
                'reason': 'No changes detected',
                'old_revision_id': 'revision_456'
            }
            
            with patch.object(detector, '_get_page_info') as mock_get_info:
                mock_get_info.return_value = {
                    "url": "https://example.com/new",
                    "path": "/new",
                    "canonical_url": "https://example.com/new",
                    "render_mode": "STATIC",
                    "is_indexable": True,
                    "metadata": {}
                }
                
                result = detector._process_url_batch(urls, existing_pages, sitemap_urls)
                
                assert len(result['unchanged']) == 1
                assert len(result['new']) == 1
                assert result['unchanged'][0]['url'] == "https://example.com"
                assert result['new'][0]['url'] == "https://example.com/new"

    @patch('worker.change_detection.requests.Session.get')
    def test_check_content_hash_detailed_no_changes(self, mock_get, mock_data_fetcher):
        """Test content hash check when no changes detected."""
        detector = ChangeDetector("project_123", "run_456", mock_data_fetcher)
        
        # Mock HTTP response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "<html><body>Test content</body></html>"
        mock_get.return_value = mock_response
        
        existing_page = {
            "id": "page_123",
            "url": "https://example.com"
        }
        
        current_revision = {
            "id": "revision_456",
            "content_sha256": hashlib.sha256("test content".encode('utf-8')).hexdigest()
        }
        
        with patch.object(detector, '_extract_normalized_content') as mock_extract:
            mock_extract.return_value = "test content"
            
            result = detector._check_content_hash_detailed("https://example.com", existing_page, current_revision)
            
            assert result['has_changed'] is False
            assert result['reason'] == 'No changes detected'
            assert result['old_revision_id'] == 'revision_456'

    @patch('worker.change_detection.requests.Session.get')
    def test_check_content_hash_detailed_changes_detected(self, mock_get, mock_data_fetcher):
        """Test content hash check when changes are detected."""
        detector = ChangeDetector("project_123", "run_456", mock_data_fetcher)
        
        # Mock HTTP response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "<html><body>Updated content</body></html>"
        mock_get.return_value = mock_response
        
        existing_page = {
            "id": "page_123",
            "url": "https://example.com"
        }
        
        current_revision = {
            "id": "revision_456",
            "content_sha256": hashlib.sha256("old content".encode('utf-8')).hexdigest()
        }
        
        with patch.object(detector, '_extract_normalized_content') as mock_extract:
            mock_extract.return_value = "updated content"
            
            result = detector._check_content_hash_detailed("https://example.com", existing_page, current_revision)
            
            assert result['has_changed'] is True
            assert 'Content hash changed' in result['reason']
            assert result['old_revision_id'] == 'revision_456'
            assert 'new_content_hash' in result

    @patch('worker.change_detection.requests.Session.get')
    def test_check_content_hash_detailed_http_error(self, mock_get, mock_data_fetcher):
        """Test content hash check with HTTP error."""
        detector = ChangeDetector("project_123", "run_456", mock_data_fetcher)
        
        # Mock HTTP error response
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response
        
        existing_page = {
            "id": "page_123",
            "url": "https://example.com"
        }
        
        current_revision = {
            "id": "revision_456",
            "content_sha256": "abc123"
        }
        
        result = detector._check_content_hash_detailed("https://example.com", existing_page, current_revision)
        
        assert result['has_changed'] is True
        assert 'HTTP 404' in result['reason']
        assert result['old_revision_id'] == 'revision_456'

    def test_extract_normalized_content(self, mock_data_fetcher):
        """Test content normalization for hashing."""
        detector = ChangeDetector("project_123", "run_456", mock_data_fetcher)
        
        html = """
        <html>
        <head>
            <title>Test Page</title>
            <script>console.log('test');</script>
            <style>body { color: red; }</style>
        </head>
        <body>
            <h1>Main Title</h1>
            <p>Some content here</p>
            <div>   Multiple   spaces   </div>
        </body>
        </html>
        """
        
        result = detector._extract_normalized_content(html)
        
        # Should remove scripts and styles
        assert 'console.log' not in result
        assert 'color: red' not in result
        
        # Should normalize whitespace
        assert 'Multiple   spaces' not in result
        assert 'Multiple spaces' in result
        
        # Should contain main content
        assert 'Main Title' in result
        assert 'Some content here' in result

    def test_get_page_info(self, mock_data_fetcher):
        """Test page info extraction."""
        detector = ChangeDetector("project_123", "run_456", mock_data_fetcher)
        
        result = detector._get_page_info("https://example.com/about")
        
        assert result["url"] == "https://example.com/about"
        assert result["path"] == "/about"
        assert result["canonical_url"] == "https://example.com/about"
        assert result["render_mode"] == "STATIC"
        assert result["is_indexable"] is True
        assert result["metadata"] == {}

    def test_save_page_revision_no_old_revision(self, mock_data_fetcher):
        """Test saving page revision when no old revision exists."""
        detector = ChangeDetector("project_123", "run_456", mock_data_fetcher)
        
        with patch.object(detector, '_extract_normalized_content') as mock_extract:
            mock_extract.return_value = "normalized content"
            
            result = detector.save_page_revision(
                page_id="page_123",
                content="<html>Test content</html>",
                title="Test Page",
                description="Test description",
                metadata={"test": "value"}
            )
            
            assert result == "revision_456"
            mock_data_fetcher.create_page_revision.assert_called_once()
            mock_data_fetcher.update_page_revision.assert_called_once_with("page_123", "revision_456")

    def test_save_page_revision_with_unchanged_content(self, mock_data_fetcher):
        """Test saving page revision when content hasn't changed."""
        detector = ChangeDetector("project_123", "run_456", mock_data_fetcher)
        
        # Mock old revision with same content hash
        old_revision = {
            "id": "revision_456",
            "content_sha256": hashlib.sha256("normalized content".encode('utf-8')).hexdigest()
        }
        mock_data_fetcher.get_revision_by_id.return_value = old_revision
        
        with patch.object(detector, '_extract_normalized_content') as mock_extract:
            mock_extract.return_value = "normalized content"
            
            result = detector.save_page_revision(
                page_id="page_123",
                content="<html>Test content</html>",
                title="Test Page",
                description="Test description",
                old_revision_id="revision_456"
            )
            
            # Should return existing revision ID without creating new one
            assert result == "revision_456"
            mock_data_fetcher.update_page_last_seen.assert_called_once_with("page_123")
            mock_data_fetcher.create_page_revision.assert_not_called()

    def test_save_page_revision_with_changed_content(self, mock_data_fetcher):
        """Test saving page revision when content has changed."""
        detector = ChangeDetector("project_123", "run_456", mock_data_fetcher)
        
        # Mock old revision with different content hash
        old_revision = {
            "id": "revision_456",
            "content_sha256": hashlib.sha256("old content".encode('utf-8')).hexdigest()
        }
        mock_data_fetcher.get_revision_by_id.return_value = old_revision
        mock_data_fetcher.create_page_revision.return_value = "revision_789"
        
        with patch.object(detector, '_extract_normalized_content') as mock_extract:
            mock_extract.return_value = "new content"
            
            result = detector.save_page_revision(
                page_id="page_123",
                content="<html>New content</html>",
                title="Test Page",
                description="Test description",
                old_revision_id="revision_456"
            )
            
            assert result == "revision_789"
            mock_data_fetcher.create_page_revision.assert_called_once()
            mock_data_fetcher.update_page_revision.assert_called_once_with("page_123", "revision_789")

    def test_save_page_revision_error_handling(self, mock_data_fetcher):
        """Test error handling in save_page_revision."""
        detector = ChangeDetector("project_123", "run_456", mock_data_fetcher)
        
        # Mock data fetcher to raise exception
        mock_data_fetcher.create_page_revision.side_effect = Exception("Database error")
        
        with patch.object(detector, '_extract_normalized_content') as mock_extract:
            mock_extract.return_value = "normalized content"
            
            result = detector.save_page_revision(
                page_id="page_123",
                content="<html>Test content</html>",
                title="Test Page"
            )
            
            assert result is None

    def test_check_page_changes_error_handling(self, mock_data_fetcher):
        """Test error handling in check_page_changes."""
        detector = ChangeDetector("project_123", "run_456", mock_data_fetcher)
        
        existing_page = {
            "id": "page_123",
            "url": "https://example.com",
            "current_revision_id": "revision_456"
        }
        
        with patch.object(detector, '_check_content_hash_detailed') as mock_check:
            mock_check.side_effect = Exception("Network error")
            
            result = detector._check_page_changes("https://example.com", existing_page)
            
            assert result['has_changed'] is True
            assert 'Error checking page' in result['reason']
            assert result['old_revision_id'] == 'revision_456'
