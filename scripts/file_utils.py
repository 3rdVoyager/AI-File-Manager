"""
File utility functions: metadata extraction, content reading, directory scanning,
content hashing, and binary file detection.
"""

import os
import hashlib
from pathlib import Path
from typing import Optional

from scripts.config import SNIPPET_START, SNIPPET_MIDDLE, SNIPPET_END, MAX_FILE_SIZE_MB
from scripts.cache import hash_content
from scripts.models import FileMetadata


def format_size(size_bytes: int) -> str:
    """Format file size in human-readable format."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.2f} TB"


def get_file_metadata(file_path: str) -> FileMetadata:
    """Extract metadata from a file and return a FileMetadata dataclass."""
    path = Path(file_path)
    stat = path.stat()
    
    return FileMetadata(
        filename=path.name,
        path=str(path),
        size_bytes=stat.st_size,
        size_human=format_size(stat.st_size),
        created="",
        modified="",
        extension=path.suffix.lower() if path.suffix else "none",
    )


def get_file_metadata_dict(file_path: str) -> dict:
    """Get file metadata as a plain dict (backward-compatible with old code)."""
    path = Path(file_path)
    stat = path.stat()
    
    return {
        "filename": path.name,
        "path": str(path),
        "size_bytes": stat.st_size,
        "size_human": format_size(stat.st_size),
        "created": "",  # st_ctime not reliable on all OS
        "modified": "",  # caller should format if needed
        "extension": path.suffix.lower() if path.suffix else "none",
    }


def read_file_content(file_path: str) -> str:
    """Read file content and extract three snippets: start, middle, end."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except UnicodeDecodeError:
        try:
            with open(file_path, "r", encoding="latin-1") as f:
                content = f.read()
        except Exception as e:
            return f"[Error reading file: {str(e)}]"
    except Exception as e:
        return f"[Error reading file: {str(e)}]"

    total = len(content)
    
    # Small file: return everything
    if total <= SNIPPET_START + SNIPPET_END:
        return content
    
    # Medium file: start + end (no middle to avoid overlap)
    if total <= SNIPPET_START + SNIPPET_MIDDLE + SNIPPET_END:
        return (
            content[:SNIPPET_START]
            + "\n\n... [Content truncated] ...\n\n"
            + content[-SNIPPET_END:]
        )
    
    # Large file: start + middle + end
    mid_start = (total // 2) - (SNIPPET_MIDDLE // 2)
    return (
        content[:SNIPPET_START]
        + "\n\n... [Content truncated - beginning] ...\n\n"
        + content[mid_start:mid_start + SNIPPET_MIDDLE]
        + "\n\n... [Content truncated - middle] ...\n\n"
        + content[-SNIPPET_END:]
    )


def read_file_content_raw(file_path: str) -> Optional[str]:
    """Read the full file content. Returns None on failure."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except UnicodeDecodeError:
        try:
            with open(file_path, "r", encoding="latin-1") as f:
                return f.read()
        except Exception:
            return None
    except Exception:
        return None


def is_large_file(file_path: str) -> bool:
    """Check if file exceeds the maximum analyzable size."""
    try:
        size_bytes = os.path.getsize(file_path)
        return size_bytes > MAX_FILE_SIZE_MB * 1024 * 1024
    except OSError:
        return True


def get_supported_extensions() -> set:
    """Return a set of file extensions that can be analyzed."""
    return {
        ".txt", ".md", ".rst", ".log",
        ".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".c", ".cpp", ".h",
        ".hpp", ".cs", ".go", ".rs", ".rb", ".php", ".swift", ".kt",
        ".html", ".htm", ".css", ".scss", ".less", ".sass",
        ".json", ".xml", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".conf",
        ".csv", ".tsv",
        ".sh", ".bat", ".ps1",
        ".sql", ".r", ".m", ".pl", ".lua",
    }


def scan_directory(directory_path: str) -> list:
    """Scan a directory for supported files, returning sorted list of file paths."""
    path = Path(directory_path)
    supported = get_supported_extensions()
    files = []
    
    for file_path in sorted(path.rglob("*")):
        if not file_path.is_file():
            continue
        # Skip hidden files/directories
        if any(part.startswith(".") for part in file_path.parts):
            continue
        if is_large_file(str(file_path)):
            continue
        if file_path.suffix.lower() in supported:
            files.append(str(file_path))
    
    return files


def compute_file_hash(file_path: str) -> str:
    """Compute a SHA-256 hash of file content. Returns empty string on failure."""
    try:
        content = read_file_content_raw(file_path)
        if content is None:
            return ""
        return hash_content(content)
    except Exception:
        return ""