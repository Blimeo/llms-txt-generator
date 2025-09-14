#!/usr/bin/env python3
"""
Test script for the scheduler service.
This script can be used to test the scheduler locally or verify it's working in production.
"""
import os
import time
import json
import requests
from redis import Redis
from dotenv import load_dotenv

load_dotenv()

REDIS_URL = os.environ.get("REDIS_URL", "rediss://default:AfdjAAIncDE0MmZlMWViNTJkNWU0MzVjOGEzOTYwOWQyOTQyNzAyYnAxNjMzMzE@hip-lobster-63331.upstash.io:6379")
redis = Redis.from_url(REDIS_URL, decode_responses=True)

SCHEDULED_JOBS_KEY = "scheduled:jobs"
IMMEDIATE_JOBS_KEY = "generate:queue"

def test_redis_connection():
    """Test Redis connection"""
    try:
        redis.ping()
        print("✅ Redis connection successful")
        return True
    except Exception as e:
        print(f"❌ Redis connection failed: {e}")
        return False

def test_scheduler_health(scheduler_url="http://localhost:8080"):
    """Test scheduler health endpoint"""
    try:
        response = requests.get(f"{scheduler_url}/health", timeout=5)
        if response.status_code == 200:
            print("✅ Scheduler health check successful")
            return True
        else:
            print(f"❌ Scheduler health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Scheduler health check failed: {e}")
        return False

def add_test_job():
    """Add a test job to the scheduled queue"""
    test_job = {
        "project_id": "test-project",
        "run_id": "test-run-123",
        "url": "https://example.com",
        "created_at": time.time()
    }
    
    # Schedule job to run in 5 seconds
    run_time = time.time() + 5
    redis.zadd(SCHEDULED_JOBS_KEY, {json.dumps(test_job): run_time})
    print(f"✅ Added test job scheduled to run at {time.ctime(run_time)}")
    return test_job

def check_job_processing():
    """Check if the test job was moved to the immediate queue"""
    immediate_jobs = redis.lrange(IMMEDIATE_JOBS_KEY, 0, -1)
    print(f"📊 Jobs in immediate queue: {len(immediate_jobs)}")
    
    for job_str in immediate_jobs:
        try:
            job = json.loads(job_str)
            if job.get("project_id") == "test-project":
                print("✅ Test job found in immediate queue!")
                return True
        except json.JSONDecodeError:
            continue
    
    print("⏳ Test job not yet processed")
    return False

def cleanup_test_data():
    """Clean up test data"""
    # Remove test jobs from both queues
    immediate_jobs = redis.lrange(IMMEDIATE_JOBS_KEY, 0, -1)
    for job_str in immediate_jobs:
        try:
            job = json.loads(job_str)
            if job.get("project_id") == "test-project":
                redis.lrem(IMMEDIATE_JOBS_KEY, 1, job_str)
        except json.JSONDecodeError:
            continue
    
    # Remove from scheduled jobs
    scheduled_jobs = redis.zrange(SCHEDULED_JOBS_KEY, 0, -1)
    for job_str in scheduled_jobs:
        try:
            job = json.loads(job_str)
            if job.get("project_id") == "test-project":
                redis.zrem(SCHEDULED_JOBS_KEY, job_str)
        except json.JSONDecodeError:
            continue
    
    print("🧹 Cleaned up test data")

def main():
    print("🧪 Testing LLMS Scheduler Service")
    print("=" * 40)
    
    # Test Redis connection
    if not test_redis_connection():
        return
    
    # Test scheduler health (optional - only if scheduler is running)
    scheduler_url = os.environ.get("SCHEDULER_URL", "http://localhost:8080")
    print(f"\n🔍 Testing scheduler health at {scheduler_url}")
    test_scheduler_health(scheduler_url)
    
    # Add test job
    print("\n📝 Adding test job...")
    add_test_job()
    
    # Wait and check if job was processed
    print("\n⏳ Waiting for scheduler to process job (up to 35 seconds)...")
    for i in range(7):  # Check every 5 seconds for 35 seconds total
        time.sleep(5)
        if check_job_processing():
            break
        print(f"   Check {i+1}/7...")
    
    # Cleanup
    print("\n🧹 Cleaning up...")
    cleanup_test_data()
    
    print("\n✅ Test completed!")

if __name__ == "__main__":
    main()
