"""
Configuration constants for AI File Manager.

All tunable values live here so they can be imported by any module.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Snippet sizes for the three-slot content extraction strategy
SNIPPET_START = 1000    # Characters from beginning
SNIPPET_MIDDLE = 1000   # Characters from middle
SNIPPET_END = 1000      # Characters from end

# Groq API
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
MODEL = "openai/gpt-oss-20b"  # Can be overridden via .env

# Reports directory (relative to project root)
REPORTS_DIR = Path(__file__).resolve().parent.parent / "reports"