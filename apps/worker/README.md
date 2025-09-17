# LLMS.txt Worker

A Python-based web crawler and content processor that generates LLMS.txt files for websites. This worker is designed to efficiently crawl websites, detect changes, and create structured text artifacts suitable for Large Language Model training and analysis.

## Purpose

The worker serves as the core processing engine for the llmstxt-crawler system, responsible for:

- **Web Crawling**: Intelligently crawling websites while respecting robots.txt and rate limits
- **Change Detection**: Detecting content changes using HTTP headers and content hashing
- **Content Processing**: Extracting and normalizing web content for LLM consumption
- **Artifact Generation**: Creating structured LLMS.txt files with crawled content
- **Storage Management**: Uploading generated files to S3-compatible storage
- **Scheduling**: Managing automated crawling schedules via Google Cloud Tasks

## Architecture

The worker is organized into focused modules:

### Core Modules

- **`crawler.py`** - Web crawling with change detection integration
- **`change_detection.py`** - Content change detection using headers and SHA256 hashing
- **`llms_generator.py`** - Generate LLMS.txt formatted content from crawl results

### Storage & Infrastructure

- **`database.py`** - Supabase client and database operations
- **`s3_storage.py`** - S3 upload operations and artifact management
- **`storage.py`** - Main storage orchestration and run status management

### Integration & Scheduling

- **`webhooks.py`** - Webhook management and execution
- **`scheduling.py`** - Cron scheduling and task management
- **`cloud_tasks_client.py`** - Google Cloud Tasks integration

### Configuration

- **`constants.py`** - Centralized configuration and constants
- **`exceptions.py`** - Custom exception classes

## Key Features

### Intelligent Change Detection

The worker implements a two-phase change detection strategy:

1. **Header-based Detection**: Uses ETag and Last-Modified headers to quickly identify unchanged content
2. **Content-based Detection**: Falls back to SHA256 hashing of normalized content when headers are unavailable or indicate changes

### Efficient Crawling

- Respects robots.txt directives
- Implements configurable rate limiting
- Processes pages in batches for optimal performance
- Supports both static and dynamic content

### Content Normalization

- Removes timestamps and dynamic content that shouldn't affect change detection
- Strips script tags, style elements, and other non-content elements
- Normalizes whitespace and extracts meaningful text content

### Automated Scheduling

- Supports cron-based scheduling (daily, weekly)
- Integrates with Google Cloud Tasks for reliable job execution
- Automatically schedules next runs based on project configuration

### Webhook Integration

- Calls configured webhooks when content changes are detected
- Includes comprehensive logging and error handling
- Supports webhook secrets for security

## Usage

### Environment Variables

Required environment variables:

```bash
# Supabase Configuration
NEXT_PUBLIC_SUPABASE_URL=your_supabase_url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_key
SUPABASE_PROJECT_ID=your_project_id

# AWS/S3 Configuration
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key

# Worker Configuration
WORKER_URL=https://your-worker-endpoint
PORT=8080

# Crawling Configuration (optional)
CRAWL_MAX_PAGES=100
CRAWL_MAX_DEPTH=2
CRAWL_DELAY=0.5
```

### Running the Worker

The worker can be run as a standalone HTTP server:

```bash
python worker.py
```

Or integrated into your application by importing the relevant modules:

```python
from worker import crawl_with_change_detection, generate_llms_text

# Crawl a website with change detection
result = crawl_with_change_detection(
    start_url="https://example.com",
    project_id="project_123",
    run_id="run_456",
    max_pages=100
)

# Generate LLMS.txt content
llms_content = generate_llms_text(result, "job_789")
```

## API Endpoints

The worker exposes the following HTTP endpoints:

- **`POST /`** - Main job processing endpoint (receives Cloud Tasks payloads)
- **`GET /health`** - Health check endpoint
- **`GET /ready`** - Readiness check endpoint

## Dependencies

Key dependencies include:

- `requests` - HTTP client for web crawling
- `beautifulsoup4` - HTML parsing and content extraction
- `boto3` - AWS SDK for S3 operations
- `supabase` - Supabase client for database operations
- `google-cloud-tasks` - Google Cloud Tasks integration

## Development

### Code Organization

The worker follows a modular architecture with clear separation of concerns:

- Each module has a single responsibility
- Constants are centralized in `constants.py`
- Error handling is standardized with custom exceptions
- Type hints are used throughout for better code quality

### Testing

The worker includes comprehensive error handling and logging to aid in debugging and monitoring.

### Contributing

When making changes:

1. Follow the existing code organization patterns
2. Update constants in `constants.py` rather than hardcoding values
3. Add appropriate type hints and docstrings
4. Ensure error handling follows the established patterns
5. Update this README if adding new functionality

## Monitoring

The worker provides detailed logging for:

- Crawling progress and results
- Change detection decisions
- S3 upload status
- Webhook execution results
- Error conditions and exceptions

Log levels can be configured via the logging system to control verbosity.