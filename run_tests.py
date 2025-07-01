#!/usr/bin/env python3
"""Test runner script for the note assistant."""

import subprocess
import sys

def run_tests():
    """Run the test suite."""
    try:
        # Run pytest with coverage
        result = subprocess.run([
            sys.executable, "-m", "pytest", 
            "tests/", 
            "-v", 
            "--cov=src",
            "--cov-report=term-missing"
        ], check=True)
        
        print("\n✅ All tests passed!")
        return 0
        
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Tests failed with exit code {e.returncode}")
        return e.returncode
    except FileNotFoundError:
        print("❌ pytest not found. Please install test dependencies:")
        print("pip install -r requirements.txt")
        return 1

if __name__ == "__main__":
    sys.exit(run_tests())