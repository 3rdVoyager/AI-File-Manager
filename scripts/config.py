"""
Configuration constants for AI File Manager.

All tunable values live here so they can be imported by any module.
This module must remain a leaf module (no imports from other scripts/ modules).
"""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# ─── Project paths ──────────────────────────────────────────────────────────

# Project root is two levels up from scripts/config.py
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Reports directory
REPORTS_DIR = PROJECT_ROOT / "reports"

# Application data directory (for cache, user settings)
APP_DATA_DIR = Path.home() / ".aifm"

# Cache database path
CACHE_DB_PATH = APP_DATA_DIR / "cache.db"

# Snippet sizes for the three-slot content extraction strategy
SNIPPET_START = 1000    # Characters from beginning
SNIPPET_MIDDLE = 1000   # Characters from middle
SNIPPET_END = 1000      # Characters from end

# ─── AI Provider ────────────────────────────────────────────────────────────

# Groq API
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

# AI Model - use GROQ_MODEL env var, fall back to default
DEFAULT_MODEL = "openai/gpt-oss-20b"
MODEL = os.getenv("GROQ_MODEL", DEFAULT_MODEL)

# Current model identifier for cache invalidation
# If the model changes, cached analyses are automatically invalidated
CURRENT_MODEL = MODEL

# API settings
AI_TIMEOUT = 30.0       # Seconds per API call
AI_TEMPERATURE = 0.15   # Low temperature for consistent JSON output
AI_MAX_TOKENS = 3000    # Max tokens in AI response
AI_RETRY_COUNT = 2      # Number of retries on failure
AI_RETRY_DELAY = 1.0    # Seconds between retries

# ─── Batch scanning ────────────────────────────────────────────────────────

MAX_FILE_SIZE_MB = 50      # Skip files larger than this
SCAN_BATCH_DELAY = 0.1     # Seconds between API calls (rate limiting)

# ─── Cache ──────────────────────────────────────────────────────────────────

# Cache schema version - bump to invalidate all caches
CACHE_SCHEMA_VERSION = 1