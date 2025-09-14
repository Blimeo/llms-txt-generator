#!/usr/bin/env python3
# apps/worker/python_worker.py
import os
import json
import time
import traceback
import logging
from datetime import datetime
import signal
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer


from redis import Redis
from dotenv import load_dotenv

# local worker modules
from worker.crawler import crawl_with_change_detection
from worker.llms_generator import generate_llms_text
from worker.storage import maybe_upload_s3_from_memory, update_run_status

load_dotenv()  # loads .env from repo root or apps/worker

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("python_worker")

REDIS_URL="rediss://default:AfdjAAIncDE0MmZlMWViNTJkNWU0MzVjOGEzOTYwOWQyOTQyNzAyYnAxNjMzMzE@hip-lobster-63331.upstash.io:6379"
if not REDIS_URL:
    raise RuntimeError("Missing REDIS_URL env var")

redis = Redis.from_url(REDIS_URL, decode_responses=True)
QUEUE_NAME = "generate:queue"
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
    # Flask/uvicorn etc would need different handling; we use this flag in main loop.
    logger.info("Received signal %s, shutting down...", signum)

# Register signals
signal.signal(signal.SIGTERM, handle_termination)
signal.signal(signal.SIGINT, handle_termination)



def process_job_payload(job: dict):
    """
    Perform crawl + llms generation with change detection. Return dict with result metadata.
    """
    job_id = job.get("id")
    url = job.get("url")
    project_id = job.get("projectId")
    run_id = job.get("runId")  # This should be passed from the API
    
    if not job_id or not url or not project_id or not run_id:
        raise ValueError("job must contain id+url+project id+run id")
    
    # Update run status to IN_PROGRESS if we have run_id
    if run_id:
        update_run_status(run_id, "IN_PROGRESS")

    # crawl site with change detection
    crawl_opts = {
        "max_pages": int(os.environ.get("CRAWL_MAX_PAGES", 100)),
        "max_depth": int(os.environ.get("CRAWL_MAX_DEPTH", 2)),
        "delay": float(os.environ.get("CRAWL_DELAY", 0.5)),
    }
    
    logger.info("starting crawl with change detection for %s with opts %s", url, crawl_opts)
    crawl_result = crawl_with_change_detection(
        url, 
        project_id, 
        run_id, 
        **crawl_opts
    )
    
    # If no changes detected, we can skip llms.txt generation
    if not crawl_result.get("changes_detected", True):
        logger.info("No changes detected, skipping llms.txt generation")
        update_run_status(run_id, "COMPLETE_NO_DIFFS", "No changes detected, skipping generation")
        return {
            "txt_path": None,
            "json_path": None,
            "s3_url_txt": None,
            "s3_url_json": None,
            "pages_crawled": 0,
            "local_files_deleted": True,
            "changes_detected": False,
            "message": "No changes detected"
        }

    logger.info("crawl finished: crawled %s pages", crawl_result.get("pages_crawled"))

    # generate llms files in memory
    txt_content, json_content = generate_llms_text(crawl_result, job_id)
    logger.info("generated llms files in memory")

    # S3 upload with database updates directly from memory
    changes_detected = crawl_result.get("changes_detected", True)
    txt_filename = f"llms_{job_id}.txt"
    json_filename = f"llms_{job_id}.json"
    
    s3_url_txt = maybe_upload_s3_from_memory(txt_content, txt_filename, run_id, project_id, changes_detected) if run_id and project_id else None
    s3_url_json = maybe_upload_s3_from_memory(json_content, json_filename, run_id, project_id, changes_detected) if run_id and project_id else None

    result = {
        "txt_path": None,  # No local files anymore
        "json_path": None,  # No local files anymore
        "s3_url_txt": s3_url_txt,
        "s3_url_json": s3_url_json,
        "pages_crawled": crawl_result.get("pages_crawled"),
        "local_files_deleted": True,  # Always true since we don't create local files
        "changes_detected": crawl_result.get("changes_detected", True),
        "changed_pages": crawl_result.get("changed_pages", []),
        "new_pages": crawl_result.get("new_pages", []),
        "unchanged_pages": crawl_result.get("unchanged_pages", [])
    }
    return result


def main():
    port = int(os.environ.get("PORT", "8080"))
    server, server_thread = start_health_server(port)
    logger.info("health server listening on port %s", port)

    logger.info("python worker: listening for jobs on %s", QUEUE_NAME)
    while not SHUTDOWN:
        try:
            item = redis.brpop(QUEUE_NAME, timeout=5)
            if SHUTDOWN:
                break
            if not item:
                continue
            _, payload = item
            job = json.loads(payload)
            job_id = job.get("id")
            if not job_id:
                logger.warning("skipping job without id: %s", job)
                continue

            logger.info("picked job %s -> %s", job_id, job)

            try:
                result = process_job_payload(job)
                logger.info("completed job %s -> %s", job_id, result)
            except Exception as ex:
                tb = traceback.format_exc()
                logger.exception("job %s failed: %s", job_id, ex)
                
                # Update run status to FAILED if we have run_id
                run_id = job.get("runId")
                if run_id:
                    update_run_status(run_id, "FAILED", str(ex))
                
                # optionally implement retry logic here (requeue, backoff)
        except KeyboardInterrupt:
            logger.info("Worker shutting down (KeyboardInterrupt)")
            break
        except Exception as e:
            logger.exception("Unexpected worker error: %s", e)
            time.sleep(2)
    try:
        server.shutdown()
    except Exception:
        pass
    logger.info("worker exited cleanly")

if __name__ == "__main__":
    main()
