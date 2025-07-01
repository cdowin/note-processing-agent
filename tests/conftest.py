"""Test configuration and fixtures for pytest."""

import sys
from pathlib import Path

# Add src to path so we can import modules
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))