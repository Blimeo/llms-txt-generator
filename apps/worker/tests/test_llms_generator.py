"""Unit tests for LLMS text generation business logic."""

import pytest
from unittest.mock import patch

from worker.llms_generator import generate_llms_text


class TestLLMSGenerator:
    """Test cases for LLMS text generation."""

    def test_generate_llms_text_with_start_page(self, sample_crawl_result):
        """Test LLMS text generation with start page found."""
        result = generate_llms_text(sample_crawl_result, "job_123")
        
        lines = result.split('\n')
        
        # Check header
        assert lines[0] == "# Example Homepage"
        assert lines[1] == ""
        
        # Check description
        assert lines[2] == "> Welcome to Example"
        assert lines[3] == ""
        
        # Check pages section
        assert lines[4] == "## Pages"
        assert lines[5] == ""
        
        # Check page entries
        assert "- [Example Homepage](https://example.com): Welcome to Example" in lines
        assert "- [About Us](https://example.com/about): Learn about our company" in lines

    def test_generate_llms_text_without_start_page(self):
        """Test LLMS text generation when start page is not found."""
        crawl_result = {
            "start_url": "https://example.com",
            "pages": [
                {
                    "url": "https://example.com/about",
                    "title": "About Us",
                    "description": "Learn about our company"
                }
            ]
        }
        
        result = generate_llms_text(crawl_result, "job_123")
        
        lines = result.split('\n')
        
        # Should use first page as project name
        assert lines[0] == "# About Us"
        assert lines[2] == "> Learn about our company"

    def test_generate_llms_text_with_empty_pages(self):
        """Test LLMS text generation with empty pages list."""
        crawl_result = {
            "start_url": "https://example.com",
            "pages": []
        }
        
        result = generate_llms_text(crawl_result, "job_123")
        
        lines = result.split('\n')
        
        # Should use domain name as project name
        assert lines[0] == "# example.com"
        assert lines[2] == "> Website content from https://example.com"
        assert lines[4] == "## Pages"
        assert lines[5] == ""

    def test_generate_llms_text_with_title_only(self):
        """Test LLMS text generation with pages that have only titles."""
        crawl_result = {
            "start_url": "https://example.com",
            "pages": [
                {
                    "url": "https://example.com",
                    "title": "Example Homepage",
                    "description": ""
                },
                {
                    "url": "https://example.com/about",
                    "title": "About Us",
                    "description": ""
                }
            ]
        }
        
        result = generate_llms_text(crawl_result, "job_123")
        
        lines = result.split('\n')
        
        # Check that pages without descriptions are formatted correctly
        assert "- [Example Homepage](https://example.com)" in lines
        assert "- [About Us](https://example.com/about)" in lines

    def test_generate_llms_text_with_url_only(self):
        """Test LLMS text generation with pages that have no title."""
        crawl_result = {
            "start_url": "https://example.com",
            "pages": [
                {
                    "url": "https://example.com",
                    "title": "",
                    "description": "Welcome to Example"
                },
                {
                    "url": "https://example.com/about",
                    "title": "",
                    "description": "Learn about our company"
                }
            ]
        }
        
        result = generate_llms_text(crawl_result, "job_123")
        
        lines = result.split('\n')
        
        # Should use URL as link title when title is empty
        assert "- [https://example.com](https://example.com): Welcome to Example" in lines
        assert "- [https://example.com/about](https://example.com/about): Learn about our company" in lines

    def test_generate_llms_text_with_missing_url(self):
        """Test LLMS text generation with pages missing URL."""
        crawl_result = {
            "start_url": "https://example.com",
            "pages": [
                {
                    "url": "https://example.com",
                    "title": "Example Homepage",
                    "description": "Welcome to Example"
                },
                {
                    "url": "",  # Missing URL
                    "title": "About Us",
                    "description": "Learn about our company"
                }
            ]
        }
        
        result = generate_llms_text(crawl_result, "job_123")
        
        lines = result.split('\n')
        
        # Should only include pages with valid URLs
        assert "- [Example Homepage](https://example.com): Welcome to Example" in lines
        assert "- [About Us](): Learn about our company" not in lines

    def test_generate_llms_text_with_fallback_description(self):
        """Test LLMS text generation with fallback description."""
        crawl_result = {
            "start_url": "https://example.com",
            "pages": [
                {
                    "url": "https://example.com",
                    "title": "Example Homepage",
                    "description": ""  # Empty description
                }
            ]
        }
        
        result = generate_llms_text(crawl_result, "job_123")
        
        lines = result.split('\n')
        
        # Should use fallback description
        assert lines[2] == "> Website content from https://example.com"

    def test_generate_llms_text_with_domain_fallback(self):
        """Test LLMS text generation with domain name fallback for project name."""
        crawl_result = {
            "start_url": "https://subdomain.example.com",
            "pages": [
                {
                    "url": "https://subdomain.example.com",
                    "title": "",  # Empty title
                    "description": "Welcome to Example"
                }
            ]
        }
        
        result = generate_llms_text(crawl_result, "job_123")
        
        lines = result.split('\n')
        
        # Should use domain name as project name
        assert lines[0] == "# subdomain.example.com"

    def test_generate_llms_text_with_complex_url(self):
        """Test LLMS text generation with complex URL structure."""
        crawl_result = {
            "start_url": "https://example.com:8080/path/to/page?param=value#fragment",
            "pages": [
                {
                    "url": "https://example.com:8080/path/to/page?param=value#fragment",
                    "title": "Complex Page",
                    "description": "A page with complex URL"
                }
            ]
        }
        
        result = generate_llms_text(crawl_result, "job_123")
        
        lines = result.split('\n')
        
        # Should use title as project name
        assert lines[0] == "# Complex Page"
        assert lines[2] == "> A page with complex URL"

    def test_generate_llms_text_with_special_characters(self):
        """Test LLMS text generation with special characters in titles and descriptions."""
        crawl_result = {
            "start_url": "https://example.com",
            "pages": [
                {
                    "url": "https://example.com",
                    "title": "Example & Company - Homepage",
                    "description": "Welcome to our site! We're #1 in the industry."
                },
                {
                    "url": "https://example.com/about",
                    "title": "About Us | Company Info",
                    "description": "Learn about our team & mission."
                }
            ]
        }
        
        result = generate_llms_text(crawl_result, "job_123")
        
        lines = result.split('\n')
        
        # Should handle special characters correctly
        assert lines[0] == "# Example & Company - Homepage"
        assert lines[2] == "> Welcome to our site! We're #1 in the industry."
        assert "- [Example & Company - Homepage](https://example.com): Welcome to our site! We're #1 in the industry." in lines
        assert "- [About Us | Company Info](https://example.com/about): Learn about our team & mission." in lines

    def test_generate_llms_text_with_whitespace_handling(self):
        """Test LLMS text generation with whitespace handling."""
        crawl_result = {
            "start_url": "https://example.com",
            "pages": [
                {
                    "url": "https://example.com",
                    "title": "  Example Homepage  ",  # Extra whitespace
                    "description": "  Welcome to Example  "  # Extra whitespace
                }
            ]
        }
        
        result = generate_llms_text(crawl_result, "job_123")
        
        lines = result.split('\n')
        
        # Should strip whitespace
        assert lines[0] == "# Example Homepage"
        assert lines[2] == "> Welcome to Example"
        assert "- [Example Homepage](https://example.com): Welcome to Example" in lines

    def test_generate_llms_text_with_multiple_pages(self):
        """Test LLMS text generation with multiple pages."""
        crawl_result = {
            "start_url": "https://example.com",
            "pages": [
                {
                    "url": "https://example.com",
                    "title": "Homepage",
                    "description": "Main page"
                },
                {
                    "url": "https://example.com/about",
                    "title": "About",
                    "description": "About us"
                },
                {
                    "url": "https://example.com/contact",
                    "title": "Contact",
                    "description": "Get in touch"
                },
                {
                    "url": "https://example.com/products",
                    "title": "Products",
                    "description": "Our products"
                }
            ]
        }
        
        result = generate_llms_text(crawl_result, "job_123")
        
        lines = result.split('\n')
        
        # Should include all pages
        assert "- [Homepage](https://example.com): Main page" in lines
        assert "- [About](https://example.com/about): About us" in lines
        assert "- [Contact](https://example.com/contact): Get in touch" in lines
        assert "- [Products](https://example.com/products): Our products" in lines

    def test_generate_llms_text_job_id_parameter(self):
        """Test that job_id parameter is accepted but not used in current implementation."""
        crawl_result = {
            "start_url": "https://example.com",
            "pages": [
                {
                    "url": "https://example.com",
                    "title": "Example Homepage",
                    "description": "Welcome to Example"
                }
            ]
        }
        
        # Should work with different job IDs
        result1 = generate_llms_text(crawl_result, "job_123")
        result2 = generate_llms_text(crawl_result, "job_456")
        
        # Results should be identical since job_id is not currently used
        assert result1 == result2
