"""Pytest configuration and shared fixtures."""

import pytest
from unittest.mock import Mock, MagicMock
from datetime import datetime
from typing import Dict, Any, List

from worker.data_fetcher import DataFetcher


@pytest.fixture
def mock_data_fetcher():
    """Create a mock DataFetcher for testing business logic."""
    mock = Mock(spec=DataFetcher)
    
    # Configure default return values
    mock.get_existing_pages_with_revisions.return_value = []
    mock.create_page_record.return_value = "page_123"
    mock.create_page_revision.return_value = "revision_456"
    mock.update_page_last_seen.return_value = True
    mock.update_page_revision.return_value = True
    mock.get_revision_by_id.return_value = None
    mock.update_run_status.return_value = True
    mock.create_run.return_value = "run_789"
    mock.get_latest_llms_txt_url.return_value = None
    mock.create_artifact_record.return_value = "artifact_101"
    mock.update_project_last_run.return_value = True
    mock.update_project_next_run.return_value = True
    mock.get_active_webhooks.return_value = []
    mock.log_webhook_event.return_value = True
    mock.get_project_config_with_domain.return_value = None
    
    return mock


@pytest.fixture
def sample_page_data():
    """Sample page data for testing."""
    return {
        "id": "page_123",
        "url": "https://example.com",
        "path": "/",
        "canonical_url": "https://example.com",
        "render_mode": "STATIC",
        "is_indexable": True,
        "current_revision_id": "revision_456",
        "current_revision": {
            "id": "revision_456",
            "content_sha256": "abc123def456",
            "created_at": "2024-01-01T00:00:00Z"
        },
        "metadata": {}
    }


@pytest.fixture
def sample_crawl_result():
    """Sample crawl result for testing."""
    return {
        "start_url": "https://example.com",
        "pages_crawled": 2,
        "max_pages": 100,
        "max_depth": 2,
        "pages": [
            {
                "url": "https://example.com",
                "title": "Example Homepage",
                "description": "Welcome to Example",
                "page_id": "page_123",
                "revision_id": "revision_456"
            },
            {
                "url": "https://example.com/about",
                "title": "About Us",
                "description": "Learn about our company",
                "page_id": "page_124",
                "revision_id": "revision_457"
            }
        ],
        "changes_detected": True,
        "changed_pages": [
            {
                "id": "page_123",
                "url": "https://example.com",
                "change_reason": "Content hash changed"
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


@pytest.fixture
def sample_job_payload():
    """Sample job payload for testing."""
    return {
        "id": "job_123",
        "url": "https://example.com",
        "projectId": "project_456",
        "runId": "run_789",
        "isScheduled": False,
        "isInitialRun": False
    }


@pytest.fixture
def sample_webhook_data():
    """Sample webhook data for testing."""
    return {
        "id": "webhook_123",
        "url": "https://webhook.example.com/callback",
        "secret": "secret_key",
        "is_active": True,
        "project_id": "project_456"
    }


@pytest.fixture
def sample_project_config():
    """Sample project configuration for testing."""
    return {
        "cron_expression": "0 2 * * *",
        "is_enabled": True,
        "next_run_at": "2024-01-02T02:00:00Z",
        "projects": {
            "domain": "https://example.com"
        }
    }
