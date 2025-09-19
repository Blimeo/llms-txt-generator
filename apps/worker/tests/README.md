# Worker Test Suite

This directory contains comprehensive unit tests for the worker application's business logic. The tests are designed to verify that the business logic works correctly by mocking the data layer (DataFetcher) instead of the Supabase client directly.

## Test Structure

```
tests/
├── __init__.py                 # Test package initialization
├── conftest.py                 # Pytest configuration and shared fixtures
├── test_data_fetcher.py        # Tests for DataFetcher class
├── test_llms_generator.py      # Tests for LLMS text generation
├── test_crawler.py             # Tests for crawler business logic
├── test_change_detection.py    # Tests for change detection logic
├── test_storage.py             # Tests for storage business logic
├── test_worker.py              # Tests for main worker process
└── README.md                   # This file
```

## Test Philosophy

The tests follow these principles:

1. **Business Logic Focus**: Tests focus on business logic rather than database operations
2. **Mocked Data Layer**: The `DataFetcher` class is mocked to provide controlled test data
3. **Comprehensive Coverage**: Tests cover happy paths, error cases, and edge cases
4. **Isolated Tests**: Each test is independent and doesn't rely on external services

## Running Tests

### Prerequisites

Install the test dependencies:

```bash
cd apps/worker
pip install -e .[test]
```

### Run All Tests

```bash
# Using the test runner script
python run_tests.py

# Or directly with pytest
pytest tests/ -v --cov=worker --cov-report=html
```

### Run Specific Test Files

```bash
# Test only the data fetcher
pytest tests/test_data_fetcher.py -v

# Test only the crawler logic
pytest tests/test_crawler.py -v

# Test with specific markers
pytest tests/ -m unit -v
```

### Run Tests with Coverage

```bash
pytest tests/ --cov=worker --cov-report=term-missing --cov-report=html
```

The HTML coverage report will be generated in `htmlcov/index.html`.

## Test Categories

### 1. DataFetcher Tests (`test_data_fetcher.py`)

Tests the data access layer that handles all Supabase database operations:

- **Project Operations**: Getting project configs, updating run times
- **Run Operations**: Creating runs, updating run status
- **Page Operations**: Getting existing pages, creating page records
- **Revision Operations**: Creating and retrieving page revisions
- **Artifact Operations**: Creating artifact records, getting latest URLs
- **Webhook Operations**: Getting active webhooks, logging events
- **Error Handling**: Database connection failures, invalid data

### 2. LLMS Generator Tests (`test_llms_generator.py`)

Tests the business logic for generating LLMS.txt formatted content:

- **Content Generation**: Creating properly formatted LLMS.txt content
- **Title Handling**: Using page titles, falling back to URLs
- **Description Handling**: Using meta descriptions, fallback descriptions
- **URL Processing**: Handling various URL formats and edge cases
- **Special Characters**: Properly escaping and handling special characters
- **Whitespace Handling**: Normalizing whitespace in titles and descriptions
- **Multiple Pages**: Processing multiple pages correctly

### 3. Crawler Tests (`test_crawler.py`)

Tests the web crawling business logic:

- **URL Normalization**: Converting relative URLs, handling fragments
- **Domain Comparison**: Checking if URLs belong to the same domain
- **HTML Extraction**: Extracting titles and meta descriptions
- **Page Record Creation**: Creating new page records in the database
- **Change Detection Integration**: Working with the change detection system
- **Error Handling**: HTTP errors, network failures, invalid responses
- **Robots.txt**: Parsing and respecting robots.txt rules
- **Rate Limiting**: Handling delays between requests

### 4. Change Detection Tests (`test_change_detection.py`)

Tests the change detection business logic:

- **Sitemap Processing**: Parsing XML sitemaps and sitemap indexes
- **Content Hashing**: Detecting changes through content hash comparison
- **Page Comparison**: Comparing existing pages with new content
- **Revision Management**: Creating and managing page revisions
- **URL Normalization**: Ensuring consistent URL comparison
- **Batch Processing**: Processing multiple URLs efficiently
- **Error Handling**: Network failures, parsing errors, database errors

### 5. Storage Tests (`test_storage.py`)

Tests the storage and status update business logic:

- **S3 Upload Integration**: Coordinating S3 uploads with database updates
- **Run Status Updates**: Updating run status with proper scheduling logic
- **Webhook Management**: Calling webhooks based on run results
- **Scheduling Logic**: Determining when to schedule next runs
- **Error Handling**: S3 failures, database errors, webhook failures
- **Status Transitions**: Proper status transitions and logging

### 6. Worker Main Process Tests (`test_worker.py`)

Tests the main worker process orchestration:

- **Job Processing**: End-to-end job processing workflow
- **Error Handling**: Graceful handling of various failure scenarios
- **Environment Variables**: Using custom and default configuration
- **HTTP Handler**: Cloud Tasks HTTP request handling
- **Status Updates**: Proper status updates throughout the process
- **Integration**: Coordinating between all worker components

## Fixtures

The `conftest.py` file provides shared fixtures for all tests:

- **`mock_data_fetcher`**: Pre-configured mock DataFetcher with default return values
- **`sample_page_data`**: Sample page data for testing
- **`sample_crawl_result`**: Sample crawl result for testing
- **`sample_job_payload`**: Sample job payload for testing
- **`sample_webhook_data`**: Sample webhook configuration
- **`sample_project_config`**: Sample project configuration

## Mock Strategy

### DataFetcher Mocking

The `DataFetcher` class is mocked to provide controlled test data:

```python
@pytest.fixture
def mock_data_fetcher():
    mock = Mock(spec=DataFetcher)
    mock.get_existing_pages_with_revisions.return_value = []
    mock.create_page_record.return_value = "page_123"
    # ... other default return values
    return mock
```

### External Service Mocking

External services are mocked using `unittest.mock`:

- **HTTP Requests**: Mocked using `requests.Session` patches
- **S3 Operations**: Mocked using `boto3` client patches
- **Cloud Tasks**: Mocked using Google Cloud Tasks client patches

## Test Data

Tests use realistic but controlled test data:

- **URLs**: Valid HTTP/HTTPS URLs with various formats
- **HTML Content**: Sample HTML with titles, meta descriptions, and content
- **Database Records**: Realistic page, revision, and artifact data
- **Job Payloads**: Complete job payloads with all required fields

## Coverage Goals

The test suite aims for:

- **80%+ Code Coverage**: All business logic should be covered
- **100% Branch Coverage**: All conditional logic should be tested
- **Error Path Coverage**: All error handling should be tested
- **Edge Case Coverage**: Boundary conditions and edge cases

## Continuous Integration

The tests are designed to run in CI environments:

- **No External Dependencies**: All external services are mocked
- **Deterministic**: Tests produce consistent results
- **Fast Execution**: Tests run quickly without network calls
- **Parallel Safe**: Tests can run in parallel without conflicts

## Debugging Tests

### Running Individual Tests

```bash
# Run a specific test method
pytest tests/test_crawler.py::TestCrawlerBusinessLogic::test_normalize_url_valid_urls -v

# Run with print statements
pytest tests/test_crawler.py -v -s

# Run with detailed output
pytest tests/test_crawler.py -v --tb=long
```

### Test Debugging Tips

1. **Use `-s` flag**: Allows print statements to show
2. **Use `--tb=long`**: Shows full traceback for failures
3. **Use `--pdb`**: Drops into debugger on failures
4. **Check fixtures**: Ensure mock data matches expectations
5. **Verify assertions**: Make sure test assertions are correct

## Adding New Tests

When adding new tests:

1. **Follow naming conventions**: `test_<function_name>_<scenario>`
2. **Use descriptive names**: Test names should explain what they test
3. **Mock external dependencies**: Don't make real network calls
4. **Test edge cases**: Include boundary conditions and error cases
5. **Update fixtures**: Add new fixtures if needed for test data
6. **Maintain coverage**: Ensure new code is covered by tests

## Example Test

```python
def test_crawl_with_change_detection_no_changes(self, mock_data_fetcher):
    """Test crawl when no changes are detected."""
    with patch('worker.crawler.ChangeDetector') as mock_change_detector_class:
        mock_detector = Mock()
        mock_detector.detect_changes.return_value = {
            "has_changes": False,
            "changed_pages": [],
            "new_pages": [],
            "unchanged_pages": [{"id": "page_123", "url": "https://example.com"}]
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
```

This test demonstrates:
- Mocking the ChangeDetector class
- Providing controlled test data
- Testing the business logic without database calls
- Asserting expected behavior
- Clear documentation of what the test verifies
