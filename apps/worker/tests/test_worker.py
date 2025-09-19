"""Unit tests for main worker process business logic."""

import pytest
from unittest.mock import Mock, patch, MagicMock
import json

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import importlib.util
spec = importlib.util.spec_from_file_location("worker_module", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "worker.py"))
worker_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(worker_module)
process_job_payload = worker_module.process_job_payload
CloudTasksHandler = worker_module.CloudTasksHandler
from worker.constants import (
    RUN_STATUS_IN_PROGRESS,
    RUN_STATUS_COMPLETE_NO_DIFFS,
    RUN_STATUS_COMPLETE_WITH_DIFFS
)


class TestWorkerMainProcess:
    """Test cases for main worker process business logic."""

    def test_process_job_payload_success(self, sample_job_payload, sample_crawl_result):
        """Test successful job processing."""
        with patch.object(worker_module, 'DataFetcher') as mock_data_fetcher_class, \
             patch.object(worker_module, 'crawl_with_change_detection') as mock_crawl, \
             patch.object(worker_module, 'generate_llms_text') as mock_generate, \
             patch.object(worker_module, 'maybe_upload_s3_from_memory') as mock_upload, \
             patch.object(worker_module, 'update_run_status') as mock_update_status:
            
            # Setup mocks
            mock_data_fetcher = Mock()
            mock_data_fetcher_class.return_value = mock_data_fetcher
            
            mock_crawl.return_value = sample_crawl_result
            mock_generate.return_value = "# Test Content\n\nTest llms.txt content"
            mock_upload.return_value = "https://example.com/llms_123.txt"
            mock_update_status.return_value = True
            
            result = process_job_payload(sample_job_payload)
            
            # Verify data fetcher was initialized
            mock_data_fetcher_class.assert_called_once()
            
            # Verify run status was updated to IN_PROGRESS
            mock_update_status.assert_any_call(
                mock_data_fetcher,
                "run_789",
                RUN_STATUS_IN_PROGRESS,
                "project_456",
                False,  # is_scheduled
                False   # is_initial_run
            )
            
            # Verify crawl was called with data fetcher
            mock_crawl.assert_called_once()
            call_args = mock_crawl.call_args
            assert call_args[0][0] == "https://example.com"  # start_url
            assert call_args[0][1] == "project_456"  # project_id
            assert call_args[0][2] == "run_789"  # run_id
            assert call_args[0][3] == mock_data_fetcher  # data_fetcher
            
            # Verify LLMS text generation
            mock_generate.assert_called_once_with(sample_crawl_result, "job_123")
            
            # Verify S3 upload
            mock_upload.assert_called_once()
            upload_args = mock_upload.call_args
            assert upload_args[0][0] == mock_data_fetcher  # data_fetcher
            assert upload_args[0][1] == "# Test Content\n\nTest llms.txt content"  # content
            assert upload_args[0][2] == "llms_job_123.txt"  # filename
            assert upload_args[0][3] == "run_789"  # run_id
            assert upload_args[0][4] == "project_456"  # project_id
            assert upload_args[0][5] is True  # changes_detected
            
            # Verify result
            assert result["s3_url_txt"] == "https://example.com/llms_123.txt"
            assert result["pages_crawled"] == 2
            assert result["changes_detected"] is True

    def test_process_job_payload_no_changes(self, sample_job_payload):
        """Test job processing when no changes are detected."""
        crawl_result_no_changes = {
            "start_url": "https://example.com",
            "pages_crawled": 0,
            "max_pages": 100,
            "max_depth": 2,
            "pages": [],
            "changes_detected": False,
            "changed_pages": [],
            "new_pages": [],
            "unchanged_pages": [{"id": "page_123", "url": "https://example.com"}]
        }
        
        with patch.object(worker_module, 'DataFetcher') as mock_data_fetcher_class, \
             patch.object(worker_module, 'crawl_with_change_detection') as mock_crawl, \
             patch.object(worker_module, 'generate_llms_text') as mock_generate, \
             patch.object(worker_module, 'maybe_upload_s3_from_memory') as mock_upload, \
             patch.object(worker_module, 'update_run_status') as mock_update_status:
            
            # Setup mocks
            mock_data_fetcher = Mock()
            mock_data_fetcher_class.return_value = mock_data_fetcher
            
            mock_crawl.return_value = crawl_result_no_changes
            mock_update_status.return_value = True
            
            result = process_job_payload(sample_job_payload)
            
            # Verify run status was updated to IN_PROGRESS first
            mock_update_status.assert_any_call(
                mock_data_fetcher,
                "run_789",
                RUN_STATUS_IN_PROGRESS,
                "project_456",
                False,  # is_scheduled
                False   # is_initial_run
            )
            
            # Verify run status was updated to COMPLETE_NO_DIFFS
            mock_update_status.assert_any_call(
                mock_data_fetcher,
                "run_789",
                RUN_STATUS_COMPLETE_NO_DIFFS,
                "project_456",
                False,  # is_scheduled
                False,  # is_initial_run
                "No changes detected, skipping generation"  # summary
            )
            
            # Verify LLMS generation and S3 upload were skipped
            mock_generate.assert_not_called()
            mock_upload.assert_not_called()
            
            # Verify result
            assert result["s3_url_txt"] is None
            assert result["pages_crawled"] == 0
            assert result["changes_detected"] is False
            assert result["message"] == "No changes detected"

    def test_process_job_payload_scheduled_run(self, sample_job_payload, sample_crawl_result):
        """Test job processing for scheduled run."""
        scheduled_job = sample_job_payload.copy()
        scheduled_job["isScheduled"] = True
        
        with patch.object(worker_module, 'DataFetcher') as mock_data_fetcher_class, \
             patch.object(worker_module, 'crawl_with_change_detection') as mock_crawl, \
             patch.object(worker_module, 'generate_llms_text') as mock_generate, \
             patch.object(worker_module, 'maybe_upload_s3_from_memory') as mock_upload, \
             patch.object(worker_module, 'update_run_status') as mock_update_status:
            
            # Setup mocks
            mock_data_fetcher = Mock()
            mock_data_fetcher_class.return_value = mock_data_fetcher
            
            mock_crawl.return_value = sample_crawl_result
            mock_generate.return_value = "# Test Content"
            mock_upload.return_value = "https://example.com/llms_123.txt"
            mock_update_status.return_value = True
            
            result = process_job_payload(scheduled_job)
            
            # Verify run status was updated with is_scheduled=True
            mock_update_status.assert_any_call(
                mock_data_fetcher,
                "run_789",
                RUN_STATUS_IN_PROGRESS,
                "project_456",
                True,   # is_scheduled
                False   # is_initial_run
            )

    def test_process_job_payload_initial_run(self, sample_job_payload, sample_crawl_result):
        """Test job processing for initial run."""
        initial_job = sample_job_payload.copy()
        initial_job["isInitialRun"] = True
        
        with patch.object(worker_module, 'DataFetcher') as mock_data_fetcher_class, \
             patch.object(worker_module, 'crawl_with_change_detection') as mock_crawl, \
             patch.object(worker_module, 'generate_llms_text') as mock_generate, \
             patch.object(worker_module, 'maybe_upload_s3_from_memory') as mock_upload, \
             patch.object(worker_module, 'update_run_status') as mock_update_status:
            
            # Setup mocks
            mock_data_fetcher = Mock()
            mock_data_fetcher_class.return_value = mock_data_fetcher
            
            mock_crawl.return_value = sample_crawl_result
            mock_generate.return_value = "# Test Content"
            mock_upload.return_value = "https://example.com/llms_123.txt"
            mock_update_status.return_value = True
            
            result = process_job_payload(initial_job)
            
            # Verify run status was updated with is_initial_run=True
            mock_update_status.assert_any_call(
                mock_data_fetcher,
                "run_789",
                RUN_STATUS_IN_PROGRESS,
                "project_456",
                False,  # is_scheduled
                True    # is_initial_run
            )

    def test_process_job_payload_missing_required_fields(self):
        """Test job processing with missing required fields."""
        incomplete_job = {
            "id": "job_123",
            "url": "https://example.com"
            # Missing projectId and runId
        }
        
        with pytest.raises(ValueError, match="job must contain id\\+url\\+project id\\+run id"):
            process_job_payload(incomplete_job)

    def test_process_job_payload_missing_id(self):
        """Test job processing with missing job ID."""
        incomplete_job = {
            "url": "https://example.com",
            "projectId": "project_456",
            "runId": "run_789"
            # Missing id
        }
        
        with pytest.raises(ValueError, match="job must contain id\\+url\\+project id\\+run id"):
            process_job_payload(incomplete_job)

    def test_process_job_payload_missing_url(self):
        """Test job processing with missing URL."""
        incomplete_job = {
            "id": "job_123",
            "projectId": "project_456",
            "runId": "run_789"
            # Missing url
        }
        
        with pytest.raises(ValueError, match="job must contain id\\+url\\+project id\\+run id"):
            process_job_payload(incomplete_job)

    def test_process_job_payload_crawl_error(self, sample_job_payload):
        """Test job processing when crawl fails."""
        with patch.object(worker_module, 'DataFetcher') as mock_data_fetcher_class, \
             patch.object(worker_module, 'crawl_with_change_detection') as mock_crawl, \
             patch.object(worker_module, 'update_run_status') as mock_update_status:
            
            # Setup mocks
            mock_data_fetcher = Mock()
            mock_data_fetcher_class.return_value = mock_data_fetcher
            
            mock_crawl.side_effect = Exception("Crawl failed")
            mock_update_status.return_value = True
            
            with pytest.raises(Exception, match="Crawl failed"):
                process_job_payload(sample_job_payload)
            
            # Verify run status was updated to IN_PROGRESS before failure
            mock_update_status.assert_called_with(
                mock_data_fetcher,
                "run_789",
                RUN_STATUS_IN_PROGRESS,
                "project_456",
                False,  # is_scheduled
                False   # is_initial_run
            )

    def test_process_job_payload_generation_error(self, sample_job_payload, sample_crawl_result):
        """Test job processing when LLMS generation fails."""
        with patch.object(worker_module, 'DataFetcher') as mock_data_fetcher_class, \
             patch.object(worker_module, 'crawl_with_change_detection') as mock_crawl, \
             patch.object(worker_module, 'generate_llms_text') as mock_generate, \
             patch.object(worker_module, 'update_run_status') as mock_update_status:
            
            # Setup mocks
            mock_data_fetcher = Mock()
            mock_data_fetcher_class.return_value = mock_data_fetcher
            
            mock_crawl.return_value = sample_crawl_result
            mock_generate.side_effect = Exception("Generation failed")
            mock_update_status.return_value = True
            
            with pytest.raises(Exception, match="Generation failed"):
                process_job_payload(sample_job_payload)

    def test_process_job_payload_upload_error(self, sample_job_payload, sample_crawl_result):
        """Test job processing when S3 upload fails."""
        with patch.object(worker_module, 'DataFetcher') as mock_data_fetcher_class, \
             patch.object(worker_module, 'crawl_with_change_detection') as mock_crawl, \
             patch.object(worker_module, 'generate_llms_text') as mock_generate, \
             patch.object(worker_module, 'maybe_upload_s3_from_memory') as mock_upload, \
             patch.object(worker_module, 'update_run_status') as mock_update_status:
            
            # Setup mocks
            mock_data_fetcher = Mock()
            mock_data_fetcher_class.return_value = mock_data_fetcher
            
            mock_crawl.return_value = sample_crawl_result
            mock_generate.return_value = "# Test Content"
            mock_upload.side_effect = Exception("Upload failed")
            mock_update_status.return_value = True
            
            with pytest.raises(Exception, match="Upload failed"):
                process_job_payload(sample_job_payload)

    def test_process_job_payload_environment_variables(self, sample_job_payload, sample_crawl_result):
        """Test job processing with custom environment variables."""
        with patch.object(worker_module, 'DataFetcher') as mock_data_fetcher_class, \
             patch.object(worker_module, 'crawl_with_change_detection') as mock_crawl, \
             patch.object(worker_module, 'generate_llms_text') as mock_generate, \
             patch.object(worker_module, 'maybe_upload_s3_from_memory') as mock_upload, \
             patch.object(worker_module, 'update_run_status') as mock_update_status, \
             patch.dict('os.environ', {
                 'CRAWL_MAX_PAGES': '50',
                 'CRAWL_MAX_DEPTH': '3',
                 'CRAWL_DELAY': '1.0'
             }):
            
            # Setup mocks
            mock_data_fetcher = Mock()
            mock_data_fetcher_class.return_value = mock_data_fetcher
            
            mock_crawl.return_value = sample_crawl_result
            mock_generate.return_value = "# Test Content"
            mock_upload.return_value = "https://example.com/llms_123.txt"
            mock_update_status.return_value = True
            
            result = process_job_payload(sample_job_payload)
            
            # Verify crawl was called with custom options
            mock_crawl.assert_called_once()
            call_kwargs = mock_crawl.call_args[1]
            assert call_kwargs["max_pages"] == 50
            assert call_kwargs["max_depth"] == 3
            assert call_kwargs["delay"] == 1.0

    def test_process_job_payload_default_environment_variables(self, sample_job_payload, sample_crawl_result):
        """Test job processing with default environment variables."""
        with patch.object(worker_module, 'DataFetcher') as mock_data_fetcher_class, \
             patch.object(worker_module, 'crawl_with_change_detection') as mock_crawl, \
             patch.object(worker_module, 'generate_llms_text') as mock_generate, \
             patch.object(worker_module, 'maybe_upload_s3_from_memory') as mock_upload, \
             patch.object(worker_module, 'update_run_status') as mock_update_status, \
             patch.dict('os.environ', {}, clear=True):  # Clear environment variables
            
            # Setup mocks
            mock_data_fetcher = Mock()
            mock_data_fetcher_class.return_value = mock_data_fetcher
            
            mock_crawl.return_value = sample_crawl_result
            mock_generate.return_value = "# Test Content"
            mock_upload.return_value = "https://example.com/llms_123.txt"
            mock_update_status.return_value = True
            
            result = process_job_payload(sample_job_payload)
            
            # Verify crawl was called with default options
            mock_crawl.assert_called_once()
            call_kwargs = mock_crawl.call_args[1]
            assert call_kwargs["max_pages"] == 100  # Default from constants
            assert call_kwargs["max_depth"] == 2    # Default from constants
            assert call_kwargs["delay"] == 0.5      # Default from constants


class TestCloudTasksHandler:
    """Test cases for CloudTasksHandler."""

    def test_do_post_success(self):
        """Test successful POST request handling."""
        # Create a proper mock request object
        mock_request = Mock()
        mock_request.makefile.return_value = Mock()
        
        with patch.object(CloudTasksHandler, 'handle'):
            handler = CloudTasksHandler(mock_request, ("127.0.0.1", 8080), None)
        
        # Mock request data
        job_data = {
            "id": "job_123",
            "url": "https://example.com",
            "projectId": "project_456",
            "runId": "run_789"
        }
        
        with patch.object(handler, 'rfile') as mock_rfile, \
             patch.object(handler, 'wfile') as mock_wfile, \
             patch.object(handler, 'send_response') as mock_send_response, \
             patch.object(handler, 'send_header') as mock_send_header, \
             patch.object(handler, 'end_headers') as mock_end_headers, \
             patch.object(worker_module, 'process_job_payload') as mock_process:
            
            # Setup request
            handler.headers = {'Content-Length': str(len(json.dumps(job_data).encode('utf-8')))}
            mock_rfile.read.return_value = json.dumps(job_data).encode('utf-8')
            
            # Mock process result
            mock_process.return_value = {
                "s3_url_txt": "https://example.com/llms_123.txt",
                "pages_crawled": 2,
                "changes_detected": True
            }
            
            handler.do_POST()
            
            # Verify response
            mock_send_response.assert_called_with(200)
            mock_send_header.assert_called_with('Content-Type', 'application/json')
            mock_end_headers.assert_called_once()
            
            # Verify process_job_payload was called
            mock_process.assert_called_once_with(job_data)
            
            # Verify response body was written
            mock_wfile.write.assert_called_once()

    def test_do_post_error(self):
        """Test POST request handling with error."""
        # Create a proper mock request object
        mock_request = Mock()
        mock_request.makefile.return_value = Mock()
        
        with patch.object(CloudTasksHandler, 'handle'):
            handler = CloudTasksHandler(mock_request, ("127.0.0.1", 8080), None)
        
        # Mock request data
        job_data = {
            "id": "job_123",
            "url": "https://example.com",
            "projectId": "project_456",
            "runId": "run_789"
        }
        
        with patch.object(handler, 'rfile') as mock_rfile, \
             patch.object(handler, 'wfile') as mock_wfile, \
             patch.object(handler, 'send_response') as mock_send_response, \
             patch.object(handler, 'send_header') as mock_send_header, \
             patch.object(handler, 'end_headers') as mock_end_headers, \
             patch.object(worker_module, 'process_job_payload') as mock_process:
            
            # Setup request
            handler.headers = {'Content-Length': str(len(json.dumps(job_data).encode('utf-8')))}
            mock_rfile.read.return_value = json.dumps(job_data).encode('utf-8')
            
            # Mock process error
            mock_process.side_effect = Exception("Processing failed")
            
            handler.do_POST()
            
            # Verify error response
            mock_send_response.assert_called_with(500)
            mock_send_header.assert_called_with('Content-Type', 'application/json')
            mock_end_headers.assert_called_once()
            
            # Verify error response body was written
            mock_wfile.write.assert_called_once()
            written_data = mock_wfile.write.call_args[0][0]
            error_response = json.loads(written_data.decode('utf-8'))
            assert "error" in error_response
            assert "Processing failed" in error_response["error"]

    def test_do_get_health_check(self):
        """Test GET request for health check."""
        # Create a proper mock request object
        mock_request = Mock()
        mock_request.makefile.return_value = Mock()
        
        with patch.object(CloudTasksHandler, 'handle'):
            handler = CloudTasksHandler(mock_request, ("127.0.0.1", 8080), None)
        
        with patch.object(handler, 'send_response') as mock_send_response, \
             patch.object(handler, 'send_header') as mock_send_header, \
             patch.object(handler, 'end_headers') as mock_end_headers, \
             patch.object(handler, 'wfile') as mock_wfile:
            
            # Test root path
            handler.path = "/"
            handler.do_GET()
            
            mock_send_response.assert_called_with(200)
            mock_send_header.assert_called_with("Content-Type", "text/plain; charset=utf-8")
            mock_end_headers.assert_called_once()
            mock_wfile.write.assert_called_with(b"OK")
            
            # Reset mocks
            mock_send_response.reset_mock()
            mock_send_header.reset_mock()
            mock_end_headers.reset_mock()
            mock_wfile.reset_mock()
            
            # Test health path
            handler.path = "/health"
            handler.do_GET()
            
            mock_send_response.assert_called_with(200)
            mock_send_header.assert_called_with("Content-Type", "text/plain; charset=utf-8")
            mock_end_headers.assert_called_once()
            mock_wfile.write.assert_called_with(b"OK")
            
            # Reset mocks
            mock_send_response.reset_mock()
            mock_send_header.reset_mock()
            mock_end_headers.reset_mock()
            mock_wfile.reset_mock()
            
            # Test ready path
            handler.path = "/ready"
            handler.do_GET()
            
            mock_send_response.assert_called_with(200)
            mock_send_header.assert_called_with("Content-Type", "text/plain; charset=utf-8")
            mock_end_headers.assert_called_once()
            mock_wfile.write.assert_called_with(b"OK")

    def test_do_get_not_found(self):
        """Test GET request for non-existent path."""
        # Create a proper mock request object
        mock_request = Mock()
        mock_request.makefile.return_value = Mock()
        
        with patch.object(CloudTasksHandler, 'handle'):
            handler = CloudTasksHandler(mock_request, ("127.0.0.1", 8080), None)
        
        with patch.object(handler, 'send_response') as mock_send_response, \
             patch.object(handler, 'end_headers') as mock_end_headers:
            
            handler.path = "/nonexistent"
            handler.do_GET()
            
            mock_send_response.assert_called_with(404)
            mock_end_headers.assert_called_once()

    def test_log_message_suppressed(self):
        """Test that log_message is suppressed."""
        # Create a proper mock request object
        mock_request = Mock()
        mock_request.makefile.return_value = Mock()
        
        with patch.object(CloudTasksHandler, 'handle'):
            handler = CloudTasksHandler(mock_request, ("127.0.0.1", 8080), None)
        
        # Should return None (suppressed)
        result = handler.log_message("test format", "arg1", "arg2")
        assert result is None
