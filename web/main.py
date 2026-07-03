"""
AI File Manager - FastAPI Web Server

REST API backend that wraps the existing scripts/ business logic.
All file operations remain in Python; the browser only requests actions.

Launch with:  python start.py
Or direct:    uvicorn web.main:app --host 127.0.0.1 --port 8000

Bound to localhost only — never exposed externally.
"""

import os
import sys
import json

# Fix Windows console encoding for unicode characters
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ('utf-8', 'utf8'):
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr.encoding and sys.stderr.encoding.lower() not in ('utf-8', 'utf8'):
    sys.stderr.reconfigure(encoding='utf-8')
import uuid
import threading
import shutil
import webbrowser
from pathlib import Path
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Ensure project root is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.analysis import scan_and_analyze, analyze_file, compute_dashboard
from scripts.query_engine import query_results, keyword_filter, get_safe_to_delete
from scripts.similarity import (
    find_duplicate_content, find_similar_filenames,
    find_screenshot_groups, find_project_groups
)
from scripts.suggestions import (
    suggest_folder_organization, suggest_groups, get_cleanup_priority
)
from scripts.reporter import save_batch_results, save_ai_response, get_reports_dir
from scripts.cache import get_cache_stats, close as close_cache
from scripts.models import AnalysisResult, ScanProgress, BatchSummary


# ─── In-memory state ─────────────────────────────────────────────────────────

# Stores the most recent scan results (list of dicts)
_current_results: list = []
_current_errors: list = []
_current_summary: Optional[dict] = None

# Active scan tracking (for progress polling)
_active_scans: dict = {}  # scan_id -> ScanProgress
_scan_results_store: dict = {}  # scan_id -> (results, errors, summary)


# ─── Request/Response models ────────────────────────────────────────────────

class ScanRequest(BaseModel):
    path: str

class AnalyzeRequest(BaseModel):
    path: str

class QueryRequest(BaseModel):
    question: str

class FilterRequest(BaseModel):
    category: Optional[str] = None
    action: Optional[str] = None
    lifecycle: Optional[str] = None
    search: Optional[str] = None
    confidence_min: Optional[int] = None
    confidence_max: Optional[int] = None

class FileActionRequest(BaseModel):
    path: str
    new_path: Optional[str] = None  # for rename/move

class LoadReportRequest(BaseModel):
    path: str


# ─── App lifecycle ──────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup/shutdown."""
    yield
    close_cache()

app = FastAPI(
    title="AI File Manager",
    version="0.3",
    lifespan=lifespan,
)


# ─── Static files ───────────────────────────────────────────────────────────

# Serve the frontend from web/static/
static_dir = Path(__file__).resolve().parent / "static"
static_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/")
async def index():
    """Serve the main application page."""
    index_path = static_dir / "index.html"
    if not index_path.exists():
        return JSONResponse(
            {"error": "Frontend not built yet. Create web/static/index.html"},
            status_code=404
        )
    return FileResponse(str(index_path))


# ─── Status endpoint ───────────────────────────────────────────────────────

@app.get("/api/status")
async def get_status():
    """Server health check and cache statistics."""
    stats = get_cache_stats()
    return {
        "status": "ok",
        "version": "0.3",
        "results_count": len(_current_results),
        "cache": stats,
    }


# ─── Scan endpoints ─────────────────────────────────────────────────────────

@app.post("/api/scan")
async def start_scan(request: ScanRequest):
    """Start a background folder scan. Returns a scan_id for progress polling."""
    directory = request.path
    
    if not os.path.isdir(directory):
        raise HTTPException(status_code=400, detail=f"Directory not found: {directory}")
    
    scan_id = str(uuid.uuid4())
    progress = ScanProgress(status="starting")
    _active_scans[scan_id] = progress
    
    def worker(sid: str, dir_path: str):
        try:
            results, errors, summary = scan_and_analyze(
                dir_path,
                progress_callback=lambda p: _active_scans.update({sid: p}),
                use_cache=True
            )
            # Store results for this scan
            _scan_results_store[sid] = (
                [r.to_dict() for r in results],
                errors,
                summary.to_dict() if hasattr(summary, "to_dict") else summary
            )
            # Also set as current global results
            global _current_results, _current_errors, _current_summary
            _current_results = _scan_results_store[sid][0]
            _current_errors = _scan_results_store[sid][1]
            _current_summary = _scan_results_store[sid][2]
            
            progress.status = "done"
            _active_scans[sid] = progress
        except Exception as e:
            progress.status = "error"
            progress.error = str(e)
            _active_scans[sid] = progress
    
    threading.Thread(target=worker, args=(scan_id, directory), daemon=True).start()
    
    return {"scan_id": scan_id, "directory": directory}


@app.get("/api/scan/status/{scan_id}")
async def get_scan_status(scan_id: str):
    """Poll the progress of an active scan."""
    progress = _active_scans.get(scan_id)
    if progress is None:
        raise HTTPException(status_code=404, detail="Scan not found")
    
    response = {
        "status": progress.status,
        "current": progress.current,
        "total": progress.total,
        "current_file": progress.current_file,
        "scanned": progress.scanned,
        "cached": progress.cached,
        "errors": progress.errors,
        "elapsed_seconds": progress.elapsed_seconds,
    }
    
    # If complete, return results too
    if progress.status == "done" and scan_id in _scan_results_store:
        results, errs, summary = _scan_results_store[scan_id]
        response["results"] = results
        response["error_details"] = errs
        response["summary"] = summary
        # Clean up
        del _scan_results_store[scan_id]
        del _active_scans[scan_id]
    
    return response


# ─── Analysis endpoints ─────────────────────────────────────────────────────

@app.post("/api/analyze")
async def analyze_single(request: AnalyzeRequest):
    """Analyze a single file."""
    file_path = request.path
    if not os.path.isfile(file_path):
        raise HTTPException(status_code=400, detail=f"File not found: {file_path}")
    
    analysis, raw, was_cached = analyze_file(file_path)
    
    if analysis is None:
        raise HTTPException(status_code=500, detail=raw)
    
    # Save individual result
    try:
        save_ai_response(file_path, raw)
    except Exception:
        pass
    
    # Add to current results
    entry = {"file": os.path.basename(file_path), "path": file_path}
    entry.update(analysis)
    global _current_results
    _current_results = [entry]
    
    return {
        "analysis": analysis,
        "was_cached": was_cached,
    }


# ─── Results endpoints ──────────────────────────────────────────────────────

@app.get("/api/results")
async def get_results():
    """Return all current analysis results."""
    return {
        "results": _current_results,
        "errors": _current_errors,
        "summary": _current_summary,
        "count": len(_current_results),
    }


@app.get("/api/dashboard")
async def get_dashboard():
    """Return computed dashboard data from current results."""
    if not _current_results:
        return {"empty": True}
    dashboard = compute_dashboard(_current_results)
    
    # Add additional stats for the new dashboard cards
    import os
    total_size = 0
    duplicate_size = 0
    trash_size = 0
    
    # Compute total size and duplicates size
    content_hashes = {}
    for r in _current_results:
        try:
            if r.get("path") and os.path.isfile(r["path"]):
                size = os.path.getsize(r["path"])
                total_size += size
                content_hash = hash(str(size) + Path(r["path"]).name)
                if content_hash in content_hashes:
                    duplicate_size += size
                else:
                    content_hashes[content_hash] = size
        except Exception:
            pass
    
    # Estimate trash candidates size
    trash_candidates = [r for r in _current_results 
                       if r.get("action") in ["Delete", "Review"] 
                       and r.get("confidence", 0) >= 70]
    for r in trash_candidates:
        try:
            if r.get("path") and os.path.isfile(r["path"]):
                trash_size += os.path.getsize(r["path"])
        except Exception:
            pass
    
    # Compute average importance
    importances = [r.get("importance", 5) for r in _current_results if r.get("importance")]
    avg_importance = sum(importances) / len(importances) if importances else 0
    
    dashboard.update({
        "projects_detected": dashboard.get("projects_count", len(set(
            r.get("project", "") for r in _current_results if r.get("project")
        ))),
        "duplicate_files": dashboard.get("duplicate_count", len(set(
            r.get("path") for r in _current_results if "duplicate" in r.get("tags", [])
        ))),
        "trash_candidates": len(trash_candidates),
        "average_importance": avg_importance,
        "total_size_bytes": total_size,
        "duplicates_size_bytes": duplicate_size,
        "trash_size_bytes": trash_size,
        "files_change": dashboard.get("total_files", 0),  # TODO: compute actual change
        "projects_change": 3,  # TODO: compute from history
    })
    
    return dashboard


@app.get("/api/dashboard/categories")
async def get_categories():
    """Return category distribution with file sizes."""
    if not _current_results:
        return {"categories": []}
    
    import os
    from collections import defaultdict
    
    category_data = defaultdict(lambda: {"files": 0, "size_bytes": 0, "color": "#888"})
    
    # Color mapping for categories
    colors = {
        "Programming": "#a855f7",
        "School": "#60a5fa",
        "Documents": "#4ade80",
        "Images": "#f59e0b",
        "Videos": "#f97316",
        "Downloads": "#ec4899",
        "Other": "#94a3b8",
        "Data": "#3b82f6",
        "System": "#6b7280",
        "Installer": "#ef4444",
        "Finance": "#10b981",
        "Work": "#6366f1",
        "Personal": "#f59e0b",
        "Media": "#ec4899",
    }
    
    for r in _current_results:
        cat = r.get("category", "Other")
        category_data[cat]["files"] += 1
        category_data[cat]["color"] = colors.get(cat, "#888")
        try:
            if r.get("path") and os.path.isfile(r["path"]):
                category_data[cat]["size_bytes"] += os.path.getsize(r["path"])
        except Exception:
            pass
    
    categories = [
        {
            "name": name,
            "files": data["files"],
            "size_bytes": data["size_bytes"],
            "color": data["color"]
        }
        for name, data in sorted(category_data.items(), key=lambda x: -x[1]["size_bytes"])
    ]
    
    return {"categories": categories}


# ─── Query endpoints ────────────────────────────────────────────────────────

@app.post("/api/query")
async def query(request: QueryRequest):
    """Natural-language query against current results."""
    if not _current_results:
        raise HTTPException(status_code=400, detail="No results to query")
    
    response = query_results(_current_results, request.question)
    return response


@app.post("/api/filter")
async def filter_results(request: FilterRequest):
    """Keyword-based filtering of current results (no AI call)."""
    if not _current_results:
        return {"results": []}
    
    kwargs = {}
    if request.category:
        kwargs["category"] = request.category
    if request.action:
        kwargs["action"] = request.action
    if request.lifecycle:
        kwargs["lifecycle"] = request.lifecycle
    if request.search:
        kwargs["search"] = request.search
    if request.confidence_min is not None:
        kwargs["confidence_min"] = request.confidence_min
    if request.confidence_max is not None:
        kwargs["confidence_max"] = request.confidence_max
    
    filtered = keyword_filter(_current_results, **kwargs)
    return {"results": filtered, "count": len(filtered)}


# ─── Analysis features endpoints ────────────────────────────────────────────

@app.get("/api/safe-to-delete")
async def safe_to_delete(min_confidence: int = 70):
    """Return files that are probably safe to delete."""
    return {"files": get_safe_to_delete(_current_results, min_confidence)}


@app.post("/api/similar")
async def similar_files(request: ScanRequest):
    """Find files with similar names to a given file."""
    filename = os.path.basename(request.path)
    similar = find_similar_filenames(_current_results, threshold=0.6)
    # Filter to matches involving the given file
    related = [
        (a, b, s) for a, b, s in similar
        if a.get("file") == filename or b.get("file") == filename
    ]
    return {"similar": related}


@app.get("/api/duplicates")
async def duplicates():
    """Find files with identical content."""
    dupes = find_duplicate_content(_current_results)
    # Convert to serializable format
    result = []
    for content_hash, entries in dupes.items():
        result.append({
            "content_hash": content_hash,
            "files": [{"name": e.get("file"), "path": e.get("path")} for e in entries],
            "count": len(entries),
        })
    return {"duplicate_groups": result}


@app.get("/api/suggestions")
async def suggestions():
    """Get folder organization suggestions."""
    return suggest_folder_organization(_current_results)


@app.get("/api/cleanup-priority")
async def cleanup_priority():
    """Get files ranked by cleanup priority."""
    ranked = get_cleanup_priority(_current_results)
    return {
        "priorities": [
            {"score": score, "file": entry.get("file"), "path": entry.get("path"),
             "action": entry.get("action"), "confidence": entry.get("confidence")}
            for score, entry in ranked
        ]
    }


# ─── Report endpoints ───────────────────────────────────────────────────────

@app.post("/api/reports/load")
async def load_report(request: LoadReportRequest):
    """Load a previously saved batch results file."""
    file_path = request.path
    if not os.path.isfile(file_path):
        raise HTTPException(status_code=400, detail=f"Report not found: {file_path}")
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to load report: {e}")
    
    global _current_results, _current_errors, _current_summary
    _current_results = data.get("results", [])
    _current_errors = data.get("error_details", [])
    _current_summary = {
        "total_files": data.get("total_files", 0),
        "analyzed": data.get("analyzed", 0),
        "errors": data.get("errors", 0),
        "directory": data.get("directory", ""),
        "analysis_date": data.get("analysis_date", ""),
    }
    
    return {
        "results": _current_results,
        "errors": _current_errors,
        "summary": _current_summary,
        "count": len(_current_results),
    }


@app.post("/api/reports/save")
async def save_report():
    """Save current results to a report file."""
    if not _current_results:
        raise HTTPException(status_code=400, detail="No results to save")
    
    directory = _current_summary.get("directory", "unknown") if _current_summary else "unknown"
    try:
        saved_path = save_batch_results(
            _current_results, _current_errors, directory, len(_current_results)
        )
        return {"path": saved_path, "filename": os.path.basename(saved_path)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save: {e}")


@app.get("/api/reports/list")
async def list_reports():
    """List all saved report files."""
    reports_dir = get_reports_dir()
    reports = []
    for f in sorted(reports_dir.glob("batch_*.json"), reverse=True)[:50]:
        try:
            stat = f.stat()
            reports.append({
                "filename": f.name,
                "path": str(f),
                "size": stat.st_size,
                "modified": stat.st_mtime,
            })
        except OSError:
            pass
    return {"reports": reports}


# ─── File operation endpoints ──────────────────────────────────────────────

@app.post("/api/file/rename")
async def rename_file(request: FileActionRequest):
    """Rename or move a file. All filesystem operations stay in Python."""
    if not request.new_path:
        raise HTTPException(status_code=400, detail="new_path is required")
    try:
        os.rename(request.path, request.new_path)
        return {"success": True, "from": request.path, "to": request.new_path}
    except OSError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/file/delete")
async def delete_file(request: FileActionRequest):
    """Delete a file (moves to recycle bin via os.remove for now)."""
    try:
        os.remove(request.path)
        # Also remove from current results
        global _current_results
        _current_results = [r for r in _current_results if r.get("path") != request.path]
        return {"success": True, "path": request.path}
    except OSError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/file/move")
async def move_file(request: FileActionRequest):
    """Move a file to a new location."""
    if not request.new_path:
        raise HTTPException(status_code=400, detail="new_path is required")
    try:
        # Ensure parent directory exists
        Path(request.new_path).parent.mkdir(parents=True, exist_ok=True)
        shutil.move(request.path, request.new_path)
        return {"success": True, "from": request.path, "to": request.new_path}
    except OSError as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── Direct launch (for python main.py --web) ──────────────────────────────

def run_server():
    """Start the server and open the browser."""
    import uvicorn
    import socket
    
    # Find an available port starting from 8000
    port = 8000
    while port < 8020:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(("127.0.0.1", port))
            sock.close()
            break
        except OSError:
            port += 1
    
    # Open browser after short delay to let server start
    def _open_browser():
        import time
        time.sleep(1.5)
        webbrowser.open(f"http://127.0.0.1:{port}")
    
    threading.Thread(target=_open_browser, daemon=True).start()
    
    print("\n  AI File Manager - Web Interface")
    print("  -----------------------------")
    print(f"  Opening http://127.0.0.1:{port} in your browser...")
    print("  Press Ctrl+C to stop the server.")
    print()
    
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")


if __name__ == "__main__":
    run_server()