"""Unit tests for DataFetcher class."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from worker.data_fetcher import DataFetcher
from worker.constants import (
    RUN_STATUS_IN_PROGRESS,
    RUN_STATUS_COMPLETE_NO_DIFFS,
    RUN_STATUS_COMPLETE_WITH_DIFFS,
    RUN_STATUS_FAILED
)


class TestDataFetcher:
    """Test cases for DataFetcher class."""

    @patch('worker.data_fetcher.get_supabase_client')
    def test_init(self, mock_get_client):
        """Test DataFetcher initialization."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        
        fetcher = DataFetcher()
        
        assert fetcher.supabase == mock_client
        mock_get_client.assert_called_once()

    @patch('worker.data_fetcher.get_supabase_client')
    def test_get_project_config_with_domain_success(self, mock_get_client):
        """Test successful project config retrieval."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        
        expected_config = {
            "cron_expression": "0 2 * * *",
            "is_enabled": True,
            "projects": {"domain": "https://example.com"}
        }
        mock_client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = expected_config
        
        fetcher = DataFetcher()
        result = fetcher.get_project_config_with_domain("project_123")
        
        assert result == expected_config
        mock_client.table.assert_called_with("project_configs")

    @patch('worker.data_fetcher.get_supabase_client')
    def test_get_project_config_with_domain_not_found(self, mock_get_client):
        """Test project config retrieval when not found."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = None
        
        fetcher = DataFetcher()
        result = fetcher.get_project_config_with_domain("project_123")
        
        assert result is None

    @patch('worker.data_fetcher.get_supabase_client')
    def test_get_project_config_with_domain_error(self, mock_get_client):
        """Test project config retrieval with error."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.side_effect = Exception("Database error")
        
        fetcher = DataFetcher()
        result = fetcher.get_project_config_with_domain("project_123")
        
        assert result is None

    @patch('worker.data_fetcher.get_supabase_client')
    def test_update_project_last_run_success(self, mock_get_client):
        """Test successful project last run update."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [{"id": "project_123"}]
        
        fetcher = DataFetcher()
        result = fetcher.update_project_last_run("project_123", "2024-01-01T00:00:00Z")
        
        assert result is True
        mock_client.table.assert_called_with("project_configs")

    @patch('worker.data_fetcher.get_supabase_client')
    def test_create_run_success(self, mock_get_client):
        """Test successful run creation."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_client.table.return_value.insert.return_value.execute.return_value.data = [{"id": "run_123"}]
        
        fetcher = DataFetcher()
        result = fetcher.create_run("project_123")
        
        assert result == "run_123"
        mock_client.table.assert_called_with("runs")

    @patch('worker.data_fetcher.get_supabase_client')
    def test_create_run_failure(self, mock_get_client):
        """Test run creation failure."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_client.table.return_value.insert.return_value.execute.return_value.data = None
        
        fetcher = DataFetcher()
        result = fetcher.create_run("project_123")
        
        assert result is None

    @patch('worker.data_fetcher.get_supabase_client')
    def test_update_run_status_success(self, mock_get_client):
        """Test successful run status update."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [{"id": "run_123"}]
        
        fetcher = DataFetcher()
        result = fetcher.update_run_status("run_123", RUN_STATUS_IN_PROGRESS, "Test summary")
        
        assert result is True
        mock_client.table.assert_called_with("runs")

    @patch('worker.data_fetcher.get_supabase_client')
    def test_update_run_status_with_finished_at(self, mock_get_client):
        """Test run status update with finished_at timestamp."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [{"id": "run_123"}]
        
        fetcher = DataFetcher()
        result = fetcher.update_run_status("run_123", RUN_STATUS_COMPLETE_WITH_DIFFS, "Completed successfully")
        
        assert result is True
        
        # Verify the update call includes finished_at
        update_call = mock_client.table.return_value.update.call_args[0][0]
        assert "finished_at" in update_call
        assert update_call["summary"] == "Completed successfully"

    @patch('worker.data_fetcher.get_supabase_client')
    def test_update_run_status_failed_with_summary(self, mock_get_client):
        """Test run status update for failed run with summary."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [{"id": "run_123"}]
        
        fetcher = DataFetcher()
        result = fetcher.update_run_status("run_123", RUN_STATUS_FAILED, "Connection timeout")
        
        assert result is True
        
        # Verify the update call includes proper failed summary
        update_call = mock_client.table.return_value.update.call_args[0][0]
        assert update_call["summary"] == "Generation failed: Connection timeout"

    @patch('worker.data_fetcher.get_supabase_client')
    def test_get_existing_pages_with_revisions_success(self, mock_get_client):
        """Test successful retrieval of existing pages with revisions."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        
        # Mock pages data
        pages_data = [
            {
                "id": "page_123",
                "url": "https://example.com",
                "current_revision_id": "revision_456"
            }
        ]
        
        # Mock revisions data
        revisions_data = [
            {
                "id": "revision_456",
                "content_sha256": "abc123",
                "created_at": "2024-01-01T00:00:00Z"
            }
        ]
        
        # Configure mock responses
        mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = pages_data
        mock_client.table.return_value.select.return_value.in_.return_value.execute.return_value.data = revisions_data
        
        fetcher = DataFetcher()
        result = fetcher.get_existing_pages_with_revisions("project_123")
        
        assert len(result) == 1
        assert result[0]["id"] == "page_123"
        assert result[0]["current_revision"]["id"] == "revision_456"

    @patch('worker.data_fetcher.get_supabase_client')
    def test_create_page_record_success(self, mock_get_client):
        """Test successful page record creation."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_client.table.return_value.insert.return_value.execute.return_value.data = [{"id": "page_123"}]
        
        page_info = {
            "url": "https://example.com",
            "path": "/",
            "canonical_url": "https://example.com",
            "render_mode": "STATIC",
            "is_indexable": True,
            "metadata": {}
        }
        
        fetcher = DataFetcher()
        result = fetcher.create_page_record("project_123", page_info)
        
        assert result == "page_123"
        mock_client.table.assert_called_with("pages")

    @patch('worker.data_fetcher.get_supabase_client')
    def test_create_page_revision_success(self, mock_get_client):
        """Test successful page revision creation."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_client.table.return_value.insert.return_value.execute.return_value.data = [{"id": "revision_456"}]
        
        fetcher = DataFetcher()
        result = fetcher.create_page_revision(
            page_id="page_123",
            run_id="run_789",
            content="<html>Test content</html>",
            content_hash="abc123def456",
            title="Test Page",
            description="Test description",
            metadata={"test": "value"}
        )
        
        assert result == "revision_456"
        mock_client.table.assert_called_with("page_revisions")

    @patch('worker.data_fetcher.get_supabase_client')
    def test_get_latest_llms_txt_url_success(self, mock_get_client):
        """Test successful retrieval of latest llms.txt URL."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        
        artifacts_data = [
            {
                "metadata": {
                    "public_url": "https://example.com/llms_123.txt"
                }
            }
        ]
        
        mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = artifacts_data
        
        fetcher = DataFetcher()
        result = fetcher.get_latest_llms_txt_url("project_123")
        
        assert result == "https://example.com/llms_123.txt"

    @patch('worker.data_fetcher.get_supabase_client')
    def test_get_latest_llms_txt_url_not_found(self, mock_get_client):
        """Test retrieval of latest llms.txt URL when not found."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = []
        
        fetcher = DataFetcher()
        result = fetcher.get_latest_llms_txt_url("project_123")
        
        assert result is None

    @patch('worker.data_fetcher.get_supabase_client')
    def test_create_artifact_record_success(self, mock_get_client):
        """Test successful artifact record creation."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_client.table.return_value.insert.return_value.execute.return_value.data = [{"id": "artifact_123"}]
        
        fetcher = DataFetcher()
        result = fetcher.create_artifact_record(
            project_id="project_123",
            run_id="run_789",
            filename="llms_123.txt",
            content="Test content",
            public_url="https://example.com/llms_123.txt"
        )
        
        assert result == "artifact_123"
        mock_client.table.assert_called_with("artifacts")

    @patch('worker.data_fetcher.get_supabase_client')
    def test_get_active_webhooks_success(self, mock_get_client):
        """Test successful retrieval of active webhooks."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        
        webhooks_data = [
            {
                "id": "webhook_123",
                "url": "https://webhook.example.com",
                "secret": "secret_key",
                "is_active": True
            }
        ]
        
        mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = webhooks_data
        
        fetcher = DataFetcher()
        result = fetcher.get_active_webhooks("project_123")
        
        assert len(result) == 1
        assert result[0]["id"] == "webhook_123"

    @patch('worker.data_fetcher.get_supabase_client')
    def test_log_webhook_event_success(self, mock_get_client):
        """Test successful webhook event logging."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_client.table.return_value.insert.return_value.execute.return_value.data = [{"id": "event_123"}]
        
        fetcher = DataFetcher()
        result = fetcher.log_webhook_event(
            webhook_id="webhook_123",
            event_type="run.complete",
            payload={"test": "data"},
            status_code=200,
            response_body="Success"
        )
        
        assert result is True
        mock_client.table.assert_called_with("webhook_events")

    @patch('worker.data_fetcher.get_supabase_client')
    def test_error_handling_generic(self, mock_get_client):
        """Test generic error handling in DataFetcher methods."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_client.table.side_effect = Exception("Database connection failed")
        
        fetcher = DataFetcher()
        
        # Test that methods return None/False on error
        assert fetcher.get_project_config_with_domain("project_123") is None
        assert fetcher.update_project_last_run("project_123", "2024-01-01T00:00:00Z") is False
        assert fetcher.create_run("project_123") is None
        assert fetcher.update_run_status("run_123", RUN_STATUS_IN_PROGRESS) is False
        assert fetcher.get_existing_pages_with_revisions("project_123") == []
        assert fetcher.create_page_record("project_123", {}) is None
        assert fetcher.create_page_revision("page_123", "run_789", "content", "hash") is None
        assert fetcher.get_latest_llms_txt_url("project_123") is None
        assert fetcher.create_artifact_record("project_123", "run_789", "file.txt", "content", "url") is None
        assert fetcher.get_active_webhooks("project_123") == []
        assert fetcher.log_webhook_event("webhook_123", "event", {}, 200, "response") is False
