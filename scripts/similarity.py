"""
Similarity detection: near-duplicate file identification using content hashing,
filename similarity, and metadata comparison.

All operations are client-side — no AI calls needed for dedup detection.
"""

import os
import re
from pathlib import Path
from collections import defaultdict
from typing import Optional

from scripts.file_utils import compute_file_hash, read_file_content_raw


def find_duplicate_content(results: list) -> dict:
    """
    Find files with identical content using SHA-256 hashing.
    
    Returns: {content_hash: [list of file entries with that hash]}
    Only includes hashes that appear more than once.
    """
    hash_map = defaultdict(list)
    
    for entry in results:
        file_path = entry.get("path", "")
        if not file_path or not os.path.isfile(file_path):
            continue
        
        file_hash = compute_file_hash(file_path)
        if file_hash:
            hash_map[file_hash].append(entry)
    
    # Filter to only duplicates
    duplicates = {h: entries for h, entries in hash_map.items() if len(entries) > 1}
    return dict(duplicates)


def find_similar_filenames(results: list, threshold: float = 0.7) -> list:
    """
    Find files with similar names using Levenshtein ratio.
    
    Returns: list of (file_a, file_b, similarity_score) tuples
    """
    similar = []
    names = [(r.get("file", ""), r) for r in results]
    
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            name_a, entry_a = names[i]
            name_b, entry_b = names[j]
            
            if not name_a or not name_b:
                continue
            
            # Skip if same file
            if entry_a.get("path") == entry_b.get("path"):
                continue
            
            # Compute similarity
            score = _levenshtein_ratio(name_a.lower(), name_b.lower())
            
            if score >= threshold:
                similar.append((entry_a, entry_b, round(score, 3)))
    
    # Sort by similarity (highest first)
    similar.sort(key=lambda x: -x[2])
    return similar


def find_screenshot_groups(results: list) -> list:
    """
    Group screenshot files by date proximity and similar naming patterns.
    
    Returns: list of groups, each group is a list of file entries
    """
    # Filter to files that look like screenshots
    screenshots = []
    for r in results:
        filename = r.get("file", "")
        tags = r.get("tags", [])
        
        # Check tags for screenshot
        if any("screenshot" in t.lower() for t in tags):
            screenshots.append(r)
            continue
        
        # Check filename patterns
        if re.search(r"(screenshot|screen.?shot|screen.?capture)", filename, re.IGNORECASE):
            screenshots.append(r)
            continue
        
        # Check for common screenshot naming patterns
        if re.match(r"^Screenshot_\d{4}", filename):
            screenshots.append(r)
            continue
    
    # Group by date proximity (same day)
    groups = defaultdict(list)
    for r in screenshots:
        # Try to extract date from filename
        date_key = _extract_date_from_filename(r.get("file", ""))
        groups[date_key].append(r)
    
    # Return groups with 2+ members
    return [g for g in groups.values() if len(g) >= 2]


def find_project_groups(results: list) -> dict:
    """
    Group files by detected project name.
    
    Returns: {project_name: [list of file entries]}
    """
    groups = defaultdict(list)
    
    for r in results:
        project = r.get("project", "") or ""
        if project:
            groups[project].append(r)
    
    return dict(groups)


def _levenshtein_ratio(s1: str, s2: str) -> float:
    """
    Compute Levenshtein distance ratio between two strings.
    Returns 0.0 (completely different) to 1.0 (identical).
    """
    if not s1 and not s2:
        return 1.0
    if not s1 or not s2:
        return 0.0
    
    # Make s1 the shorter
    if len(s1) > len(s2):
        s1, s2 = s2, s1
    
    len_s1, len_s2 = len(s1), len(s2)
    
    # Use two-row optimization
    prev_row = list(range(len_s2 + 1))
    
    for i, c1 in enumerate(s1):
        curr_row = [i + 1]
        for j, c2 in enumerate(s2):
            cost = 0 if c1 == c2 else 1
            curr_row.append(min(
                curr_row[j] + 1,        # deletion
                prev_row[j + 1] + 1,    # insertion
                prev_row[j] + cost      # substitution
            ))
        prev_row = curr_row
    
    distance = prev_row[len_s2]
    max_len = max(len_s1, len_s2)
    return 1.0 - (distance / max_len)


def _extract_date_from_filename(filename: str) -> str:
    """
    Try to extract a date from a filename.
    Returns a date string like '2024-01-15' or 'unknown'.
    """
    # Pattern: Screenshot_2024-01-15_123456.png
    match = re.search(r"(\d{4})[-_]?(\d{2})[-_]?(\d{2})", filename)
    if match:
        return f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
    
    # Pattern: 20240115
    match = re.search(r"(\d{4})(\d{2})(\d{2})", filename)
    if match:
        return f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
    
    return "unknown"