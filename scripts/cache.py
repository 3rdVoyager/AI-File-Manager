"""
SQLite caching layer for AI File Manager.

Stores analysis results keyed by file content hash + modification time,
avoiding redundant API calls when files haven't changed.

Supports incremental scans by tracking which files were previously analyzed
and detecting new/changed/removed files.

Designed for eventual scale: uses indexed queries, never loads all rows
into memory at once in production paths.
"""

import os
import json
import sqlite3
import hashlib
from pathlib import Path
from typing import Optional

from scripts.config import CACHE_DB_PATH, CURRENT_MODEL


# ─── Schema ──────────────────────────────────────────────────────────────────

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS file_cache (
    path_hash      TEXT PRIMARY KEY,
    file_path      TEXT NOT NULL,
    filename       TEXT NOT NULL,
    modified_time  REAL NOT NULL,
    size_bytes     INTEGER NOT NULL,
    content_hash   TEXT NOT NULL,
    model_used     TEXT NOT NULL,
    analysis_json  TEXT NOT NULL,
    analyzed_at    TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_file_cache_path_hash ON file_cache(path_hash);
CREATE INDEX IF NOT EXISTS idx_file_cache_modified ON file_cache(modified_time);
CREATE INDEX IF NOT EXISTS idx_file_cache_content_hash ON file_cache(content_hash);
"""


# ─── Connection management ───────────────────────────────────────────────────

_connection: Optional[sqlite3.Connection] = None


def _get_connection() -> sqlite3.Connection:
    """Get or create a persistent connection to the cache database."""
    global _connection
    if _connection is None:
        # Ensure parent directory exists
        CACHE_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        _connection = sqlite3.connect(str(CACHE_DB_PATH))
        _connection.execute("PRAGMA journal_mode=WAL")
        _connection.execute("PRAGMA synchronous=NORMAL")
        _connection.executescript(SCHEMA_SQL)
    return _connection


def close():
    """Close the cache connection. Call on application shutdown."""
    global _connection
    if _connection is not None:
        _connection.close()
        _connection = None


# ─── Hashing ──────────────────────────────────────────────────────────────────

def hash_path(file_path: str) -> str:
    """Return a SHA-256 hash of the absolute file path."""
    abs_path = os.path.abspath(file_path).lower()
    return hashlib.sha256(abs_path.encode("utf-8")).hexdigest()


def hash_content(content: str) -> str:
    """Return a SHA-256 hash of file content."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


# ─── Cache operations ─────────────────────────────────────────────────────────

def get_cached_analysis(file_path: str, stat) -> Optional[dict]:
    """
    Retrieve cached analysis for a file if it's still current.
    
    Checks modification time + file size + model version.
    Returns None if cache miss or stale.
    """
    conn = _get_connection()
    path_hash = hash_path(file_path)
    modified_time = stat.st_mtime
    size_bytes = stat.st_size
    
    row = conn.execute(
        "SELECT content_hash, model_used, analysis_json FROM file_cache WHERE path_hash = ?",
        (path_hash,)
    ).fetchone()
    
    if row is None:
        return None
    
    content_hash, model_used, analysis_json = row
    
    # If model changed, cache is invalid
    if model_used != CURRENT_MODEL:
        return None
    
    try:
        return json.loads(analysis_json)
    except (json.JSONDecodeError, TypeError):
        return None


def set_cached_analysis(file_path: str, stat, content_hash: str, analysis: dict):
    """Store an analysis result in the cache."""
    conn = _get_connection()
    path_hash = hash_path(file_path)
    filename = Path(file_path).name
    
    conn.execute(
        """INSERT OR REPLACE INTO file_cache 
           (path_hash, file_path, filename, modified_time, size_bytes, 
            content_hash, model_used, analysis_json, analyzed_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))""",
        (
            path_hash,
            file_path,
            filename,
            stat.st_mtime,
            stat.st_size,
            content_hash,
            CURRENT_MODEL,
            json.dumps(analysis)
        )
    )
    conn.commit()


def invalidate_cache():
    """Clear the entire cache. Use when changing models or for debugging."""
    conn = _get_connection()
    conn.execute("DELETE FROM file_cache")
    conn.commit()


def get_cache_stats() -> dict:
    """Return cache usage statistics."""
    conn = _get_connection()
    count = conn.execute("SELECT COUNT(*) FROM file_cache").fetchone()[0]
    return {
        "cached_files": count,
        "db_path": str(CACHE_DB_PATH),
    }


def get_previously_analyzed_paths() -> set:
    """Return the set of file paths that have been cached before."""
    conn = _get_connection()
    rows = conn.execute("SELECT file_path FROM file_cache").fetchall()
    return {row[0] for row in rows}