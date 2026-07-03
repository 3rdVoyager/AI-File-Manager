"""
Output formatting and report persistence.

Handles saving analysis results as JSON, printing formatted output
to the terminal, and generating summary statistics.
"""

import json
from pathlib import Path
from datetime import datetime

from scripts.config import REPORTS_DIR


def get_reports_dir() -> Path:
    """Ensure the reports directory exists and return its path."""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    return REPORTS_DIR


def save_ai_response(file_path: str, ai_response: str) -> str:
    """Save the AI response as a .json file in the reports/ directory."""
    input_path = Path(file_path)
    reports_dir = get_reports_dir()
    
    # Create a subdirectory named after the source directory to avoid name collisions
    source_dir = input_path.parent.name or "root"
    target_dir = reports_dir / source_dir
    target_dir.mkdir(parents=True, exist_ok=True)
    
    output_path = target_dir / f"{input_path.stem}.json"
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(ai_response)
    
    return str(output_path)


def save_batch_results(results: list, errors: list, directory_path: str, total_files: int) -> str:
    """Save the combined batch results JSON to the reports directory."""
    output = {
        "analysis_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "directory": directory_path,
        "total_files": total_files,
        "analyzed": len(results),
        "errors": len(errors),
        "results": results,
        "error_details": errors,
    }
    
    source_dir_name = Path(directory_path).name or "root"
    reports_dir = get_reports_dir()
    output_path = reports_dir / f"batch_{source_dir_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)
    
    return str(output_path)


def print_progress_bar(current: int, total: int, filename: str, bar_width: int = 20):
    """Print a single-line progress bar with filename."""
    filled = int(bar_width * current / total)
    bar = "█" * filled + "░" * (bar_width - filled)
    # Truncate long filenames to fit terminal width (~80 chars)
    name = filename if len(filename) <= 40 else "..." + filename[-37:]
    print(f"\r  [{bar}] {current}/{total}  {name:<40}", end="", flush=True)


def print_single_analysis(analysis: dict):
    """Print a parsed analysis dict in human-readable format."""
    print("=" * 40)
    print("AI Analysis Result:")
    print("=" * 40)
    print(f"  Summary:      {analysis.get('summary', 'N/A')}")
    print(f"  Category:     {analysis.get('category', 'N/A')}")
    print(f"  Subcategory:  {analysis.get('subcategory', 'N/A')}")
    print(f"  Project:      {analysis.get('project', 'N/A')}")
    print(f"  Tags:         {', '.join(analysis.get('tags', [])) or 'N/A'}")
    print(f"  Importance:   {analysis.get('importance', 'N/A')}/10")
    print(f"  Sentimental:  {analysis.get('sentimental_value', 'N/A')}/10")
    print(f"  Lifecycle:    {analysis.get('lifecycle', 'N/A')}")
    print(f"  Action:       {analysis.get('action', 'N/A')}")
    print(f"  Confidence:   {analysis.get('confidence', 'N/A')}%")
    print(f"  Reasoning:    {analysis.get('reasoning', 'N/A')}")
    print(f"  Suggested:    {analysis.get('suggested_filename', 'N/A')}")
    print("=" * 40)


def print_batch_summary(total: int, results: list, errors: list):
    """Print a summary table after batch mode completes."""
    print("\n" + "=" * 40)
    print("Batch Analysis Complete")
    print("=" * 40)
    print(f"  Total files:   {total}")
    print(f"  Analyzed:      {len(results)}")
    print(f"  Errors:        {len(errors)}")
    
    if results:
        action_counts = {}
        for r in results:
            action = r.get("action", "Unknown")
            action_counts[action] = action_counts.get(action, 0) + 1
        
        print()
        print("Actions recommended:")
        for action, count in sorted(action_counts.items(), key=lambda x: -x[1]):
            print(f"  {action:<12} {count}")
    
    if errors:
        print()
        print("Errors:")
        for e in errors:
            print(f"  {Path(e['file']).name}: {e['error']}")