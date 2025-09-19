"""Unit tests for storage business logic."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from worker.storage import (
    get_latest_llms_txt_url,
    maybe_upload_s3_from_memory,
    update_run_status
)
from worker.constants import (
    RUN_STATUS_IN_PROGRESS,
    RUN_STATUS_COMPLETE_NO_DIFFS,
    RUN_STATUS_COMPLETE_WITH_DIFFS,
    RUN_STATUS_FAILED
)


class TestStorageBusinessLogic:
    """Test cases for storage business logic."""

    def test_get_latest_llms_txt_url_success(self, mock_data_fetcher):
        """Test successful retrieval of latest llms.txt URL."""
        mock_data_fetcher.get_latest_llms_txt_url.return_value = "https://example.com/llms_123.txt"
        
        result = get_latest_llms_txt_url(mock_data_fetcher, "project_123")
        
        assert result == "https://example.com/llms_123.txt"
        mock_data_fetcher.get_latest_llms_txt_url.assert_called_once_with("project_123")

    def test_get_latest_llms_txt_url_not_found(self, mock_data_fetcher):
        """Test retrieval when no llms.txt URL is found."""
        mock_data_fetcher.get_latest_llms_txt_url.return_value = None
        
        result = get_latest_llms_txt_url(mock_data_fetcher, "project_123")
        
        assert result is None

    def test_get_latest_llms_txt_url_error(self, mock_data_fetcher):
        """Test error handling in get_latest_llms_txt_url."""
        mock_data_fetcher.get_latest_llms_txt_url.side_effect = Exception("Database error")
        
        result = get_latest_llms_txt_url(mock_data_fetcher, "project_123")
        
        assert result is None

    @patch('worker.storage.upload_content_to_s3')
    def test_maybe_upload_s3_from_memory_success(self, mock_upload_s3, mock_data_fetcher):
        """Test successful S3 upload and database update."""
        mock_upload_s3.return_value = "https://example.com/llms_123.txt"
        mock_data_fetcher.create_artifact_record.return_value = "artifact_123"
        mock_data_fetcher.update_run_status.return_value = True
        
        with patch('worker.storage.update_run_status') as mock_update_status:
            mock_update_status.return_value = True
            
            result = maybe_upload_s3_from_memory(
                data_fetcher=mock_data_fetcher,
                content="Test content",
                filename="llms_123.txt",
                run_id="run_456",
                project_id="project_123",
                changes_detected=True,
                is_scheduled=False,
                is_initial_run=False
            )
            
            assert result == "https://example.com/llms_123.txt"
            mock_upload_s3.assert_called_once_with("Test content", "llms_123.txt")
            mock_data_fetcher.create_artifact_record.assert_called_once()
            mock_update_status.assert_called_once()

    @patch('worker.storage.upload_content_to_s3')
    def test_maybe_upload_s3_from_memory_s3_failure(self, mock_upload_s3, mock_data_fetcher):
        """Test S3 upload failure."""
        mock_upload_s3.return_value = None
        
        result = maybe_upload_s3_from_memory(
            data_fetcher=mock_data_fetcher,
            content="Test content",
            filename="llms_123.txt",
            run_id="run_456",
            project_id="project_123"
        )
        
        assert result is None
        mock_data_fetcher.create_artifact_record.assert_not_called()

    @patch('worker.storage.upload_content_to_s3')
    def test_maybe_upload_s3_from_memory_artifact_failure(self, mock_upload_s3, mock_data_fetcher):
        """Test artifact record creation failure."""
        mock_upload_s3.return_value = "https://example.com/llms_123.txt"
        mock_data_fetcher.create_artifact_record.return_value = None
        
        result = maybe_upload_s3_from_memory(
            data_fetcher=mock_data_fetcher,
            content="Test content",
            filename="llms_123.txt",
            run_id="run_456",
            project_id="project_123"
        )
        
        assert result is None

    @patch('worker.storage.upload_content_to_s3')
    def test_maybe_upload_s3_from_memory_error_handling(self, mock_upload_s3, mock_data_fetcher):
        """Test error handling in maybe_upload_s3_from_memory."""
        mock_upload_s3.side_effect = Exception("S3 error")
        
        result = maybe_upload_s3_from_memory(
            data_fetcher=mock_data_fetcher,
            content="Test content",
            filename="llms_123.txt",
            run_id="run_456",
            project_id="project_123"
        )
        
        assert result is None

    def test_update_run_status_success(self, mock_data_fetcher):
        """Test successful run status update."""
        mock_data_fetcher.update_run_status.return_value = True
        mock_data_fetcher.update_project_last_run.return_value = True
        
        with patch('worker.storage.schedule_next_run') as mock_schedule, \
             patch('worker.storage.call_webhooks_for_project') as mock_webhooks:
            
            result = update_run_status(
                data_fetcher=mock_data_fetcher,
                run_id="run_123",
                status=RUN_STATUS_COMPLETE_WITH_DIFFS,
                project_id="project_123",
                is_scheduled=False,
                is_initial_run=False,
                summary="Completed successfully",
                llms_txt_url="https://example.com/llms_123.txt"
            )
            
            assert result is True
            mock_data_fetcher.update_run_status.assert_called_once_with("run_123", RUN_STATUS_COMPLETE_WITH_DIFFS, "Completed successfully")
            mock_data_fetcher.update_project_last_run.assert_called_once()
            mock_webhooks.assert_called_once_with("project_123", "run_123", "https://example.com/llms_123.txt")

    def test_update_run_status_with_scheduling(self, mock_data_fetcher):
        """Test run status update with scheduling."""
        mock_data_fetcher.update_run_status.return_value = True
        mock_data_fetcher.update_project_last_run.return_value = True
        
        with patch('worker.storage.schedule_next_run') as mock_schedule, \
             patch('worker.storage.call_webhooks_for_project') as mock_webhooks:
            
            result = update_run_status(
                data_fetcher=mock_data_fetcher,
                run_id="run_123",
                status=RUN_STATUS_COMPLETE_WITH_DIFFS,
                project_id="project_123",
                is_scheduled=True,
                is_initial_run=False,
                summary="Completed successfully"
            )
            
            assert result is True
            mock_schedule.assert_called_once_with("project_123")

    def test_update_run_status_with_initial_run(self, mock_data_fetcher):
        """Test run status update with initial run."""
        mock_data_fetcher.update_run_status.return_value = True
        mock_data_fetcher.update_project_last_run.return_value = True
        
        with patch('worker.storage.schedule_next_run') as mock_schedule, \
             patch('worker.storage.call_webhooks_for_project') as mock_webhooks:
            
            result = update_run_status(
                data_fetcher=mock_data_fetcher,
                run_id="run_123",
                status=RUN_STATUS_COMPLETE_WITH_DIFFS,
                project_id="project_123",
                is_scheduled=False,
                is_initial_run=True,
                summary="Initial run completed"
            )
            
            assert result is True
            mock_schedule.assert_called_once_with("project_123")

    def test_update_run_status_no_scheduling_for_immediate_run(self, mock_data_fetcher):
        """Test that immediate runs don't trigger scheduling."""
        mock_data_fetcher.update_run_status.return_value = True
        mock_data_fetcher.update_project_last_run.return_value = True
        
        with patch('worker.storage.schedule_next_run') as mock_schedule, \
             patch('worker.storage.call_webhooks_for_project') as mock_webhooks:
            
            result = update_run_status(
                data_fetcher=mock_data_fetcher,
                run_id="run_123",
                status=RUN_STATUS_COMPLETE_WITH_DIFFS,
                project_id="project_123",
                is_scheduled=False,
                is_initial_run=False,
                summary="Immediate run completed"
            )
            
            assert result is True
            mock_schedule.assert_not_called()

    def test_update_run_status_failed_run(self, mock_data_fetcher):
        """Test run status update for failed run."""
        mock_data_fetcher.update_run_status.return_value = True
        mock_data_fetcher.update_project_last_run.return_value = True
        
        with patch('worker.storage.schedule_next_run') as mock_schedule, \
             patch('worker.storage.call_webhooks_for_project') as mock_webhooks:
            
            result = update_run_status(
                data_fetcher=mock_data_fetcher,
                run_id="run_123",
                status=RUN_STATUS_FAILED,
                project_id="project_123",
                is_scheduled=True,
                is_initial_run=False,
                summary="Connection timeout"
            )
            
            assert result is True
            mock_data_fetcher.update_run_status.assert_called_once_with("run_123", RUN_STATUS_FAILED, "Generation failed: Connection timeout")
            mock_schedule.assert_not_called()  # Failed runs don't trigger scheduling
            mock_webhooks.assert_not_called()  # Failed runs don't trigger webhooks

    def test_update_run_status_webhook_without_url(self, mock_data_fetcher):
        """Test webhook calling when no URL is provided."""
        mock_data_fetcher.update_run_status.return_value = True
        mock_data_fetcher.update_project_last_run.return_value = True
        mock_data_fetcher.get_latest_llms_txt_url.return_value = "https://example.com/llms_456.txt"
        
        with patch('worker.storage.schedule_next_run') as mock_schedule, \
             patch('worker.storage.call_webhooks_for_project') as mock_webhooks:
            
            result = update_run_status(
                data_fetcher=mock_data_fetcher,
                run_id="run_123",
                status=RUN_STATUS_COMPLETE_WITH_DIFFS,
                project_id="project_123",
                is_scheduled=False,
                is_initial_run=False,
                summary="Completed successfully"
                # No llms_txt_url provided
            )
            
            assert result is True
            mock_data_fetcher.get_latest_llms_txt_url.assert_called_once_with("project_123")
            mock_webhooks.assert_called_once_with("project_123", "run_123", "https://example.com/llms_456.txt")

    def test_update_run_status_webhook_no_url_available(self, mock_data_fetcher):
        """Test webhook calling when no URL is available."""
        mock_data_fetcher.update_run_status.return_value = True
        mock_data_fetcher.update_project_last_run.return_value = True
        mock_data_fetcher.get_latest_llms_txt_url.return_value = None
        
        with patch('worker.storage.schedule_next_run') as mock_schedule, \
             patch('worker.storage.call_webhooks_for_project') as mock_webhooks:
            
            result = update_run_status(
                data_fetcher=mock_data_fetcher,
                run_id="run_123",
                status=RUN_STATUS_COMPLETE_WITH_DIFFS,
                project_id="project_123",
                is_scheduled=False,
                is_initial_run=False,
                summary="Completed successfully"
            )
            
            assert result is True
            mock_webhooks.assert_not_called()  # No webhooks called when no URL available

    def test_update_run_status_scheduled_run_with_diffs(self, mock_data_fetcher):
        """Test webhook calling for scheduled run with diffs."""
        mock_data_fetcher.update_run_status.return_value = True
        mock_data_fetcher.update_project_last_run.return_value = True
        
        with patch('worker.storage.schedule_next_run') as mock_schedule, \
             patch('worker.storage.call_webhooks_for_project') as mock_webhooks:
            
            result = update_run_status(
                data_fetcher=mock_data_fetcher,
                run_id="run_123",
                status=RUN_STATUS_COMPLETE_WITH_DIFFS,  # Diffs detected
                project_id="project_123",
                is_scheduled=True,  # Scheduled run
                is_initial_run=False,
                summary="Scheduled run with changes",
                llms_txt_url="https://example.com/llms_123.txt"
            )
            
            assert result is True
            mock_webhooks.assert_called_once()  # Webhooks called for scheduled run with diffs

    def test_update_run_status_scheduled_run_no_diffs(self, mock_data_fetcher):
        """Test webhook calling for scheduled run without diffs."""
        mock_data_fetcher.update_run_status.return_value = True
        mock_data_fetcher.update_project_last_run.return_value = True
        
        with patch('worker.storage.schedule_next_run') as mock_schedule, \
             patch('worker.storage.call_webhooks_for_project') as mock_webhooks:
            
            result = update_run_status(
                data_fetcher=mock_data_fetcher,
                run_id="run_123",
                status=RUN_STATUS_COMPLETE_NO_DIFFS,  # No diffs
                project_id="project_123",
                is_scheduled=True,  # Scheduled run
                is_initial_run=False,
                summary="Scheduled run without changes",
                llms_txt_url="https://example.com/llms_123.txt"
            )
            
            assert result is True
            mock_webhooks.assert_not_called()  # No webhooks for scheduled run without diffs

    def test_update_run_status_no_project_id(self, mock_data_fetcher):
        """Test run status update without project_id."""
        mock_data_fetcher.update_run_status.return_value = True
        
        with patch('worker.storage.schedule_next_run') as mock_schedule, \
             patch('worker.storage.call_webhooks_for_project') as mock_webhooks:
            
            result = update_run_status(
                data_fetcher=mock_data_fetcher,
                run_id="run_123",
                status=RUN_STATUS_COMPLETE_WITH_DIFFS,
                project_id=None,  # No project ID
                is_scheduled=False,
                is_initial_run=False,
                summary="Completed successfully"
            )
            
            assert result is True
            mock_schedule.assert_not_called()
            mock_webhooks.assert_not_called()

    def test_update_run_status_database_failure(self, mock_data_fetcher):
        """Test run status update when database update fails."""
        mock_data_fetcher.update_run_status.return_value = False
        
        result = update_run_status(
            data_fetcher=mock_data_fetcher,
            run_id="run_123",
            status=RUN_STATUS_COMPLETE_WITH_DIFFS,
            project_id="project_123",
            is_scheduled=False,
            is_initial_run=False,
            summary="Completed successfully"
        )
        
        assert result is False

    def test_update_run_status_error_handling(self, mock_data_fetcher):
        """Test error handling in update_run_status."""
        mock_data_fetcher.update_run_status.side_effect = Exception("Database error")
        
        result = update_run_status(
            data_fetcher=mock_data_fetcher,
            run_id="run_123",
            status=RUN_STATUS_COMPLETE_WITH_DIFFS,
            project_id="project_123",
            is_scheduled=False,
            is_initial_run=False,
            summary="Completed successfully"
        )
        
        assert result is False

    def test_update_run_status_project_last_run_failure(self, mock_data_fetcher):
        """Test run status update when project last_run_at update fails."""
        mock_data_fetcher.update_run_status.return_value = True
        mock_data_fetcher.update_project_last_run.return_value = False  # Failure
        
        with patch('worker.storage.schedule_next_run') as mock_schedule, \
             patch('worker.storage.call_webhooks_for_project') as mock_webhooks:
            
            result = update_run_status(
                data_fetcher=mock_data_fetcher,
                run_id="run_123",
                status=RUN_STATUS_COMPLETE_WITH_DIFFS,
                project_id="project_123",
                is_scheduled=False,
                is_initial_run=False,
                summary="Completed successfully"
            )
            
            # Should still return True even if project update fails
            assert result is True
