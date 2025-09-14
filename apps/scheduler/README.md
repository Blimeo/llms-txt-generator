# LLMS Scheduler Service

This is a standalone scheduler service that processes scheduled jobs from Redis sorted sets and moves ready jobs to the immediate queue for processing by the worker service.

## Overview

The scheduler service:
- Monitors the `scheduled:jobs` Redis sorted set
- Moves jobs that are ready to run to the `generate:queue` for immediate processing
- Runs a health check server on port 8080 (configurable via `PORT` environment variable)
- Processes jobs every 30 seconds

## Environment Variables

- `REDIS_URL`: Redis connection URL (required)
- `PORT`: Health check server port (default: 8080)

## Development

### Local Development

```bash
# Install dependencies
uv sync

# Run the scheduler directly
uv run scheduler.py

# Or run via Turbo (recommended for monorepo development)
turbo run dev --filter=@llmstxt/scheduler
```

### Development with Other Services

```bash
# Run all services together (from project root)
turbo run dev

# Run only worker and scheduler
turbo run dev --filter=@blimeo/worker --filter=@llmstxt/scheduler
```

### Docker

```bash
# Build the image
docker build -t llms-scheduler .

# Run the container
docker run -p 8080:8080 -e REDIS_URL=your_redis_url llms-scheduler
```

## Deployment

This service is designed to be deployed as a separate Google Cloud Run service alongside the main worker service. Both services share the same Redis instance for coordination.

### Google Cloud Run Deployment

1. Build and push the Docker image to Google Container Registry
2. Deploy as a Cloud Run service with:
   - Port: 8080
   - Environment variables: `REDIS_URL`
   - CPU: 1 (or minimal)
   - Memory: 512Mi (or minimal)
   - Concurrency: 1 (since it's a single-threaded scheduler)

## Health Checks

The service exposes a health check endpoint at `/health` and `/ready` that returns HTTP 200 when the service is running properly.

## Monitoring

The scheduler logs:
- When it finds and processes scheduled jobs
- Any errors during job processing
- Health check server status
- Shutdown events
