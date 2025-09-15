#!/usr/bin/env python3
# apps/worker/cloud_tasks_worker.py
import os
import json
import traceback
import logging
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
import threading

from dotenv import load_dotenv

# local worker modules
from worker.crawler import crawl_with_change_detection
from worker.llms_generator import generate_llms_text
from worker.storage import maybe_upload_s3_from_memory, update_run_status

load_dotenv()  # loads .env from repo root or apps/worker

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("cloud_tasks_worker")

class CloudTasksHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        """Handle Cloud Tasks HTTP requests"""
        try:
            # Get content length
            content_length = int(self.headers.get('Content-Length', 0))
            
            # Read the request body
            post_data = self.rfile.read(content_length)
            
            # Parse the job data from Cloud Tasks
            job_data = json.loads(post_data.decode('utf-8'))
            logger.info(f"Received Cloud Task: {job_data}")
            
            # Process the job
            result = process_job_payload(job_data)
            
            # Send success response
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(result).encode('utf-8'))
            
        except Exception as e:
            logger.exception(f"Error processing Cloud Task: {e}")
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            error_response = {"error": str(e)}
            self.wfile.write(json.dumps(error_response).encode('utf-8'))

    def do_GET(self):
        """Health check endpoint"""
        if self.path in ("/", "/health", "/ready"):
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"OK")
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        """Suppress default logging"""
        return



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
    
    # Start HTTP server for Cloud Tasks
    server = HTTPServer(("0.0.0.0", port), CloudTasksHandler)
    logger.info("Cloud Tasks worker listening on port %s", port)
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Worker shutting down (KeyboardInterrupt)")
    except Exception as e:
        logger.exception("Unexpected worker error: %s", e)
    finally:
        try:
            server.shutdown()
        except Exception:
            pass
        logger.info("worker exited cleanly")

if __name__ == "__main__":
    main()
