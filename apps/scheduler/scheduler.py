#!/usr/bin/env python3
"""
Scheduler service that processes scheduled jobs from Redis sorted sets.
This service runs as a standalone service and moves ready jobs to the immediate queue.
"""
import os
import time
import logging
import signal
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from redis import Redis
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("scheduler")

REDIS_URL = os.environ.get("REDIS_URL", "rediss://default:AfdjAAIncDE0MmZlMWViNTJkNWU0MzVjOGEzOTYwOWQyOTQyNzAyYnAxNjMzMzE@hip-lobster-63331.upstash.io:6379")
redis = Redis.from_url(REDIS_URL, decode_responses=True)

SCHEDULED_JOBS_KEY = "scheduled:jobs"
IMMEDIATE_JOBS_KEY = "generate:queue"
SHUTDOWN = False


def start_health_server(port: int = 8080):
    """
    Runs a tiny HTTP server that responds 200 on / and /health.
    Runs in a daemon thread so it won't block shutdown.
    """
    class HealthHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path in ("/", "/health", "/ready"):
                self.send_response(200)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.end_headers()
                self.wfile.write(b"OK")
            else:
                self.send_response(404)
                self.end_headers()

        # quiet the default logging
        def log_message(self, format, *args):
            return

    server = HTTPServer(("0.0.0.0", port), HealthHandler)

    def serve():
        try:
            server.serve_forever()
        except Exception:
            pass

    thread = threading.Thread(target=serve, daemon=True)
    thread.start()
    return server, thread


def handle_termination(signum, frame):
    global SHUTDOWN
    SHUTDOWN = True
    logger.info("Received signal %s, shutting down...", signum)


# Register signals
signal.signal(signal.SIGTERM, handle_termination)
signal.signal(signal.SIGINT, handle_termination)


def process_scheduled_jobs():
    """
    Process scheduled jobs that are ready to run.
    """
    try:
        # Get jobs that are ready (score <= current time)
        now = time.time()
        ready_jobs = redis.zrangebyscore(SCHEDULED_JOBS_KEY, 0, now)
        
        if not ready_jobs:
            return 0
        
        logger.info(f"Found {len(ready_jobs)} ready scheduled jobs")
        
        # Remove ready jobs from scheduled set
        redis.zremrangebyscore(SCHEDULED_JOBS_KEY, 0, now)
        
        # Move each job to immediate queue
        for job_str in ready_jobs:
            try:
                # Add to immediate queue
                redis.rpush(IMMEDIATE_JOBS_KEY, job_str)
                logger.info(f"Moved scheduled job to immediate queue: {job_str[:100]}...")
            except Exception as e:
                logger.error(f"Error moving job to immediate queue: {e}")
        
        return len(ready_jobs)
        
    except Exception as e:
        logger.error(f"Error processing scheduled jobs: {e}")
        return 0


def main():
    port = int(os.environ.get("PORT", "8080"))
    server, server_thread = start_health_server(port)
    logger.info("Scheduler health server listening on port %s", port)

    logger.info("Scheduler: processing scheduled jobs every 60 seconds")
    
    while not SHUTDOWN:
        try:
            processed_count = process_scheduled_jobs()
            if processed_count > 0:
                logger.info(f"Processed {processed_count} scheduled jobs")
            
            # Sleep for 60 seconds before next check
            time.sleep(60)
            
        except KeyboardInterrupt:
            logger.info("Scheduler shutting down (KeyboardInterrupt)")
            break
        except Exception as e:
            logger.exception("Unexpected scheduler error: %s", e)
            time.sleep(5)  # Shorter sleep on error
    
    try:
        server.shutdown()
    except Exception:
        pass
    logger.info("Scheduler exited cleanly")


if __name__ == "__main__":
    main()
