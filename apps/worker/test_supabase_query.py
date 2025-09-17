#!/usr/bin/env python3
"""
Test script to directly test the schedule_next_run function.
This script imports and calls the actual schedule_next_run function from storage.py.
"""

import os
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()  # loads .env from repo root or apps/worker

# Import the actual function from storage.py
from worker.storage import schedule_next_run

def main():
    """Test the schedule_next_run function directly"""
    project_id = "b5de7ee8-19e7-47d1-8cc5-1103d3771efb"
    run_id = "test-run-123"  # Using a test run ID
    
    print(f"Testing schedule_next_run function")
    print(f"Project ID: {project_id}")
    print(f"Run ID: {run_id}")
    print("-" * 50)
    
    try:
        # Call the actual schedule_next_run function
        result = schedule_next_run(project_id, run_id)
        
        print(f"schedule_next_run returned: {result}")
        
        if result:
            print("✅ schedule_next_run completed successfully")
        else:
            print("❌ schedule_next_run returned False")
            
    except Exception as e:
        print(f"❌ Error calling schedule_next_run: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
