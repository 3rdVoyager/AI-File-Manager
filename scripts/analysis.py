"""
Analysis pipeline: orchestrates file scanning, caching, AI analysis,
and result aggregation for both single-file and batch operations.

This module is the central coordination point — it replaces duplicated
scanning logic that previously lived in both main.py and gui.py.
"""

import os
import time
import json
from pathlib import Path
from datetime import datetime
from typing import Callable, Optional, Tuple

from scripts.models import AnalysisResult, BatchSummary, ScanProgress
from scripts.cache import (
    get_cached_analysis, set_cached_analysis, 
    get_previously_analyzed_paths, hash_content
)
from scripts.ai_client import analyze_single_file
from scripts.file_utils import (
    get_file_metadata, get_file_metadata_dict, read_file_content,
    scan_directory, compute_file_hash, is_large_file
)
from scripts.reporter import save_batch_results


def analyze_file(file_path: str, use_cache: bool = True) -> Tuple[Optional[dict], str, bool]:
    """
    Analyze a single file with caching support.
    
    Returns: (analysis_dict_or_None, raw_json_or_error, was_cached)
    """
    stat_result = None
    cached = False
    
    # Check cache first
    if use_cache:
        try:
            stat_result = os.stat(file_path)
            cached_analysis = get_cached_analysis(file_path, stat_result)
            if cached_analysis is not None:
                return cached_analysis, json.dumps(cached_analysis, indent=2), True
        except OSError:
            pass
    
    # API call
    analysis, raw = analyze_single_file(
        file_path, read_file_content, get_file_metadata_dict
    )
    
    # Store in cache if successful
    if analysis is not None and use_cache:
        try:
            if stat_result is None:
                stat_result = os.stat(file_path)
            file_hash = compute_file_hash(file_path)
            set_cached_analysis(file_path, stat_result, file_hash, analysis)
        except Exception:
            pass  # Cache failure is non-critical
    
    return analysis, raw, cached


def scan_and_analyze(
    directory_path: str,
    progress_callback: Optional[Callable[[ScanProgress], None]] = None,
    use_cache: bool = True,
    on_file_complete: Optional[Callable[[int, int, str], None]] = None,
) -> Tuple[list, list, BatchSummary]:
    """
    Full pipeline: scan directory → analyze files (with caching) → aggregate results.
    
    Args:
        directory_path: Path to scan
        progress_callback: Called with ScanProgress after each file
        use_cache: Whether to use SQLite cache
        on_file_complete: Legacy callback (index, total, filename) for backward compat
    
    Returns: (results, errors, summary)
    """
    start_time = time.time()
    
    # Phase 1: Scan
    progress = ScanProgress(status="scanning", current=0, total=0)
    if progress_callback:
        progress_callback(progress)
    
    files = scan_directory(directory_path)
    total = len(files)
    
    progress.total = total
    progress.status = "analyzing"
    
    results = []
    errors = []
    
    previously_analyzed = set()
    if use_cache:
        try:
            previously_analyzed = get_previously_analyzed_paths()
        except Exception:
            pass
    
    # Phase 2: Analyze each file
    for i, file_path in enumerate(files, 1):
        filename = Path(file_path).name
        
        # Update progress
        progress.current = i
        progress.current_file = filename
        progress.elapsed_seconds = time.time() - start_time
        if progress_callback:
            progress_callback(progress)
        if on_file_complete:
            on_file_complete(i, total, filename)
        
        try:
            analysis, raw, was_cached = analyze_file(file_path, use_cache=use_cache)
            
            if was_cached:
                progress.cached += 1
            else:
                progress.scanned += 1
            
            if analysis is not None:
                # Convert to AnalysisResult for type safety
                entry = AnalysisResult(
                    file=filename,
                    path=file_path,
                    summary=analysis.get("summary", ""),
                    category=analysis.get("category", "Other"),
                    subcategory=analysis.get("subcategory", ""),
                    tags=analysis.get("tags", []),
                    project=analysis.get("project", ""),
                    importance=analysis.get("importance", 5),
                    sentimental_value=analysis.get("sentimental_value", 1),
                    confidence=analysis.get("confidence", 50),
                    lifecycle=analysis.get("lifecycle", "Unknown"),
                    action=analysis.get("action", "Review"),
                    reasoning=analysis.get("reasoning", ""),
                    suggested_filename=analysis.get("suggested_filename", ""),
                    requires_review=analysis.get("requires_review", False),
                )
                results.append(entry)
            else:
                errors.append({
                    "file": filename,
                    "path": file_path,
                    "error": raw  # raw contains error message
                })
                progress.errors += 1
        except Exception as e:
            errors.append({
                "file": filename,
                "path": file_path,
                "error": str(e)
            })
            progress.errors += 1
    
    # Phase 3: Aggregate results
    summary = _aggregate_results(results, errors, total, directory_path, start_time)
    summary.cached = progress.cached
    summary.new_files = total - len(previously_analyzed)
    
    progress.status = "done"
    if progress_callback:
        progress_callback(progress)
    
    # Save batch results
    try:
        results_dicts = [r.to_dict() for r in results]
        save_batch_results(results_dicts, errors, directory_path, total)
    except Exception:
        pass  # Save failure is non-critical
    
    return results, errors, summary


def _aggregate_results(
    results: list, errors: list, total: int,
    directory_path: str, start_time: float
) -> BatchSummary:
    """Aggregate individual analysis results into a BatchSummary."""
    summary = BatchSummary(
        total_files=total,
        analyzed=len(results),
        errors=len(errors),
        scan_date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        directory=directory_path,
        duration_seconds=round(time.time() - start_time, 2),
    )
    
    categories = {}
    lifecycle_counts = {}
    projects = {}
    largest = []
    
    for r in results:
        # Action counts
        if r.action == "Keep":
            summary.keep_count += 1
        elif r.action == "Delete":
            summary.delete_count += 1
        elif r.action == "Archive":
            summary.archive_count += 1
        else:
            summary.review_count += 1
        
        # Category breakdown
        cat = r.category or "Other"
        categories[cat] = categories.get(cat, 0) + 1
        
        # Lifecycle
        lc = r.lifecycle or "Unknown"
        lifecycle_counts[lc] = lifecycle_counts.get(lc, 0) + 1
        
        # Projects
        if r.project:
            proj = r.project
            if proj not in projects:
                projects[proj] = []
            projects[proj].append(r.file)
        
        # Confidence distribution
        if r.confidence < 60:
            summary.confidence_low += 1
        elif r.confidence <= 85:
            summary.confidence_medium += 1
        else:
            summary.confidence_high += 1
        
        # Needs review
        if r.requires_review or r.confidence < 60:
            summary.needs_review.append(r.file)
        
        # Track largest files (by checking filesystem)
        try:
            size = os.path.getsize(r.path)
            largest.append((size, r.file, r.path))
        except OSError:
            pass
    
    # Sort largest
    largest.sort(key=lambda x: -x[0])
    summary.largest_files = [
        {"size_bytes": s, "file": f, "path": p}
        for s, f, p in largest[:10]
    ]
    
    summary.categories = dict(sorted(categories.items(), key=lambda x: -x[1]))
    summary.lifecycle_counts = dict(sorted(lifecycle_counts.items(), key=lambda x: -x[1]))
    summary.projects = dict(sorted(projects.items(), key=lambda x: -len(x[1]), reverse=True))
    
    return summary


def compute_dashboard(results: list) -> dict:
    """
    Compute full dashboard data from analysis results.
    Used by the GUI dashboard panel.
    """
    if not results:
        return {"empty": True}
    
    # Convert dict results to AnalysisResult if needed
    entries = []
    for r in results:
        if isinstance(r, dict):
            entries.append(AnalysisResult.from_dict(r))
        elif isinstance(r, AnalysisResult):
            entries.append(r)
        else:
            entries.append(r)
    
    # Filter by action
    safe_to_delete = [
        r for r in entries
        if r.action == "Delete" and r.confidence >= 70 and not r.requires_review
    ]
    
    needs_review = [
        r for r in entries
        if r.requires_review or r.action == "Review" or r.confidence < 60
    ]
    
    # Tag aggregation
    all_tags = {}
    for r in entries:
        for tag in r.tags:
            all_tags[tag] = all_tags.get(tag, 0) + 1
    
    return {
        "total_files": len(entries),
        "safe_to_delete": len(safe_to_delete),
        "needs_review": len(needs_review),
        "action_breakdown": {
            "Keep": sum(1 for r in entries if r.action == "Keep"),
            "Delete": sum(1 for r in entries if r.action == "Delete"),
            "Archive": sum(1 for r in entries if r.action == "Archive"),
            "Review": sum(1 for r in entries if r.action == "Review"),
        },
        "categories": dict(sorted(
            {r.category: sum(1 for e in entries if e.category == r.category)
             for r in entries}.items(),
            key=lambda x: -x[1]
        )),
        "tag_cloud": dict(sorted(all_tags.items(), key=lambda x: -x[1])[:20]),
        "confidence_distribution": {
            "low": sum(1 for r in entries if r.confidence < 60),
            "medium": sum(1 for r in entries if 60 <= r.confidence <= 85),
            "high": sum(1 for r in entries if r.confidence > 85),
        },
    }