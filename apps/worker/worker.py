#!/usr/bin/env python3
# apps/worker/python_worker.py
import os
import json
import time
import traceback
import logging
from datetime import datetime
import os
import signal
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer


from redis import Redis
from dotenv import load_dotenv

# local worker modules
from worker.crawler import crawl
from worker.llms_generator import generate_llms_text
from worker.storage import save_local, maybe_upload_s3

load_dotenv()  # loads .env from repo root or apps/worker

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("python_worker")

REDIS_URL="rediss://default:AfdjAAIncDE0MmZlMWViNTJkNWU0MzVjOGEzOTYwOWQyOTQyNzAyYnAxNjMzMzE@hip-lobster-63331.upstash.io:6379"
if not REDIS_URL:
    raise RuntimeError("Missing REDIS_URL env var")

redis = Redis.from_url(REDIS_URL, decode_responses=True)
QUEUE_NAME = "generate:queue"
JOB_KEY_PREFIX = "job:"
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

def set_job_hash(job_id, mapping):
    key = f"{JOB_KEY_PREFIX}{job_id}"
    # use hset with mapping
    redis.hset(key, mapping=mapping)


def get_job_hash(job_id):
    key = f"{JOB_KEY_PREFIX}{job_id}"
    return redis.hgetall(key)


def process_job_payload(job: dict):
    """
    Perform crawl + llms generation. Return dict with result metadata.
    """
    job_id = job.get("id")
    url = job.get("url")
    if not job_id or not url:
        raise ValueError("job must contain id and url")

    # crawl site
    crawl_opts = {
        "max_pages": int(os.environ.get("CRAWL_MAX_PAGES", 100)),
        "max_depth": int(os.environ.get("CRAWL_MAX_DEPTH", 2)),
        "delay": float(os.environ.get("CRAWL_DELAY", 0.5)),
    }
    logger.info("starting crawl for %s with opts %s", url, crawl_opts)
    crawl_result = crawl(url, **crawl_opts)

    logger.info("crawl finished: crawled %s pages", crawl_result.get("pages_crawled"))

    # generate llms files
    txt_path, json_path = generate_llms_text(crawl_result, job_id)
    logger.info("generated llms files: %s, %s", txt_path, json_path)

    # optionally move to designated output dir
    output_dir = os.environ.get("OUTPUT_DIR")  # e.g. /artifacts
    final_txt = save_local(txt_path, output_dir) if output_dir else txt_path
    final_json = save_local(json_path, output_dir) if output_dir else json_path

    # optional S3 upload
    s3_url_txt = maybe_upload_s3(final_txt)
    s3_url_json = maybe_upload_s3(final_json)

    result = {
        "txt_path": final_txt,
        "json_path": final_json,
        "s3_url_txt": s3_url_txt,
        "s3_url_json": s3_url_json,
        "pages_crawled": crawl_result.get("pages_crawled"),
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
            set_job_hash(job_id, {
                "status": "processing",
                "attempts": str(int(get_job_hash(job_id).get("attempts", "0")) + 1),
                "started_at": datetime.utcnow().isoformat() + "Z"
            })

            try:
                result = process_job_payload(job)
                # mark success
                set_job_hash(job_id, {
                    "status": "completed",
                    "result": json.dumps(result),
                    "finished_at": datetime.utcnow().isoformat() + "Z"
                })
                logger.info("completed job %s -> %s", job_id, result)
            except Exception as ex:
                tb = traceback.format_exc()
                logger.exception("job %s failed: %s", job_id, ex)
                set_job_hash(job_id, {
                    "status": "failed",
                    "error": str(ex),
                    "error_trace": tb,
                    "finished_at": datetime.utcnow().isoformat() + "Z"
                })
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
