#!/usr/bin/env python3
"""
AI File Manager - Web Entry Point

Launches the local FastAPI web interface.

Usage:
    python start.py              # Launch web interface
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from web.main import run_server


if __name__ == "__main__":
    run_server()