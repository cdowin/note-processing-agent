#!/usr/bin/env python3
"""
Simple launcher script for note processing.

This script can be run manually or scheduled with cron for automatic processing.
"""

import os
import sys
from pathlib import Path

# Add src to path so imports work
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Load environment variables from .env if it exists
env_file = Path(__file__).parent / ".env"
if env_file.exists():
    from dotenv import load_dotenv
    load_dotenv(env_file)

# Import and run main
from main import main

if __name__ == "__main__":
    main()