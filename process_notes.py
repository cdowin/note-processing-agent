#!/usr/bin/env python3
"""
Simple launcher script for note processing.

This script can be run manually or scheduled with cron for automatic processing.
"""

import sys
import subprocess
from pathlib import Path

# Load environment variables from .env if it exists
env_file = Path(__file__).parent / ".env"
if env_file.exists():
    from dotenv import load_dotenv
    load_dotenv(env_file)

# Run the main module
if __name__ == "__main__":
    # Change to the project directory
    project_dir = Path(__file__).parent
    
    # Run as a module to handle imports correctly
    result = subprocess.run(
        [sys.executable, "-m", "src.main"],
        cwd=project_dir
    )
    
    sys.exit(result.returncode)