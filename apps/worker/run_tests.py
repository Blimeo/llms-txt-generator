#!/usr/bin/env python3
"""Test runner script for the worker application."""

import sys
import subprocess
import os


def run_tests():
    """Run the test suite with pytest."""
    # Change to the worker directory
    worker_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(worker_dir)
    
    # Run pytest with coverage (coverage threshold is set in pytest.ini)
    cmd = [
        sys.executable, "-m", "pytest",
        "tests/",
        "-v",
        "--tb=short",
        "--cov=worker",
        "--cov-report=term-missing",
        "--cov-report=html:htmlcov"
    ]
    
    print("Running worker tests...")
    print(f"Command: {' '.join(cmd)}")
    print("-" * 50)
    
    try:
        result = subprocess.run(cmd, check=True)
        print("\n" + "=" * 50)
        print("✅ All tests passed!")
        print("📊 Coverage report generated in htmlcov/")
        return 0
    except subprocess.CalledProcessError as e:
        print("\n" + "=" * 50)
        print("❌ Tests failed!")
        return e.returncode
    except FileNotFoundError:
        print("❌ pytest not found. Please install test dependencies:")
        print("   pip install -e .[test]")
        return 1


if __name__ == "__main__":
    sys.exit(run_tests())
