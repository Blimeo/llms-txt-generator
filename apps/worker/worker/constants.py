# apps/worker/worker/constants.py
"""
Constants used throughout the worker application.
"""

# HTTP and Network
DEFAULT_USER_AGENT = "llms-txt-crawler/1.0 (+https://example.com)"
DEFAULT_TIMEOUT = 15
HEAD_TIMEOUT = 10
REQUEST_TIMEOUT = 30

# Crawling defaults
DEFAULT_MAX_PAGES = 200
DEFAULT_MAX_DEPTH = 2
DEFAULT_CRAWL_DELAY = 0.5
DEFAULT_BATCH_SIZE = 10

# Content types
HTML_CONTENT_TYPES = {"text/html", "application/xhtml+xml"}

# S3 and Storage
S3_BUCKET_NAME = "llms-txt"
S3_REGION = "us-west-1"
DEFAULT_CONTENT_TYPE = "text/plain"

# Cloud Tasks
CLOUD_TASKS_PROJECT_ID = "api-project-1042553923996"
CLOUD_TASKS_LOCATION = "us-west1"
CLOUD_TASKS_QUEUE_NAME = "llms-txt"

# Run statuses
RUN_STATUS_IN_PROGRESS = "IN_PROGRESS"
RUN_STATUS_COMPLETE_NO_DIFFS = "COMPLETE_NO_DIFFS"
RUN_STATUS_COMPLETE_WITH_DIFFS = "COMPLETE_WITH_DIFFS"
RUN_STATUS_FAILED = "FAILED"

# Cron expressions
CRON_DAILY_2AM = "0 2 * * *"
CRON_WEEKLY_SUNDAY_2AM = "0 2 * * 0"

# File naming
LLMS_TXT_FILENAME_PREFIX = "llms_"
LLMS_TXT_FILENAME_SUFFIX = ".txt"

# Database table names
TABLE_PAGES = "pages"
TABLE_PAGE_REVISIONS = "page_revisions"
TABLE_PROJECTS = "projects"
TABLE_PROJECT_CONFIGS = "project_configs"
TABLE_RUNS = "runs"
TABLE_ARTIFACTS = "artifacts"
TABLE_WEBHOOKS = "webhooks"
TABLE_WEBHOOK_EVENTS = "webhook_events"

# Artifact types
ARTIFACT_TYPE_LLMS_TXT = "LLMS_TXT"

# Webhook configuration
WEBHOOK_TIMEOUT = 30
WEBHOOK_USER_AGENT = "llmstxt-crawler/1.0"
WEBHOOK_HEADER_SECRET = "X-Webhook-Secret"
WEBHOOK_CONTENT_TYPE = "application/json"

# Environment variable names
ENV_SUPABASE_URL = "NEXT_PUBLIC_SUPABASE_URL"
ENV_SUPABASE_KEY = "NEXT_PUBLIC_SUPABASE_ANON_KEY"
ENV_SUPABASE_PROJECT_ID = "SUPABASE_PROJECT_ID"
ENV_AWS_ACCESS_KEY_ID = "AWS_ACCESS_KEY_ID"
ENV_AWS_SECRET_ACCESS_KEY = "AWS_SECRET_ACCESS_KEY"
ENV_WORKER_URL = "WORKER_URL"
ENV_PORT = "PORT"
ENV_CRAWL_MAX_PAGES = "CRAWL_MAX_PAGES"
ENV_CRAWL_MAX_DEPTH = "CRAWL_MAX_DEPTH"
ENV_CRAWL_DELAY = "CRAWL_DELAY"

# Default port
DEFAULT_PORT = 8080

# Content extraction patterns (simplified)

# Sitemap XML namespace
SITEMAP_NAMESPACE = "http://www.sitemaps.org/schemas/sitemap/0.9"
