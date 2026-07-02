#!/usr/bin/env python3
"""
AI File Manager - Main Entry Point

Analyzes files using an LLM (via Groq API) to classify, summarize, and recommend
actions (Keep/Delete/Archive). Sends three strategic content snippets (beginning,
middle, end) from each file along with metadata for AI analysis.

Supports single-file analysis (`python main.py` then enter a path) and batch
folder analysis (`python main.py` then enter `folder:C:/path/to/folder`).

After a batch scan, enters interactive query mode where you can ask natural-language
questions about the analyzed files (e.g. "show me all inactive Python projects").

Reports are saved as JSON to the reports/ directory.
"""

import os
import json
from pathlib import Path

from scripts.config import GROQ_API_KEY
from scripts.file_utils import get_file_metadata, read_file_content, scan_directory
from scripts.ai_client import analyze_single_file
from scripts.reporter import (
    save_ai_response,
    save_batch_results,
    print_progress_bar,
    print_single_analysis,
    print_batch_summary,
)
from scripts.query_engine import run_query_loop


def main():
    """Main entry point."""
    print("AI File Manager - Version 0.2")
    print("=" * 40)
    
    # Get input from user
    user_input = input("Enter the path to a file (or folder:path or reports:path): ").strip()
    
    if not user_input:
        print("Error: No input provided.")
        return
    
    # Remove surrounding quotes if present
    user_input = user_input.strip('"').strip("'")
    
    # Detect mode
    is_folder = user_input.lower().startswith("folder:")
    is_reports = user_input.lower().startswith("reports:")
    
    if is_folder:
        raw_path = user_input[7:].strip().strip('"').strip("'")
    elif is_reports:
        raw_path = user_input[8:].strip().strip('"').strip("'")
    else:
        raw_path = user_input
    
    # Normalize path
    raw_path = raw_path.replace('\\', '/')
    resolved_path = os.path.abspath(os.path.normpath(raw_path))
    
    if is_reports:
        # Load a previous batch results file for querying
        if not os.path.isfile(resolved_path):
            print(f"Error: Reports file not found: {resolved_path}")
            return
        _run_reports_mode(resolved_path)
    elif is_folder:
        if not os.path.isdir(resolved_path):
            print(f"Error: Directory not found: {resolved_path}")
            return
        _run_batch_mode(resolved_path)
    else:
        if not os.path.isfile(resolved_path):
            print(f"Error: File not found: {resolved_path}")
            print("\nTip: Use forward slashes (/) or double backslashes (\\\\) in Windows paths")
            print("Example: C:/Users/joshi/Downloads/test.txt")
            print("Or use folder: prefix to scan a directory, e.g. folder:C:/Users/joshi/Downloads")
            print("Or use reports: prefix to query a saved batch, e.g. reports:reports/batch_test_20260702.json")
            return
        _run_single_file_mode(resolved_path)


def _run_single_file_mode(file_path):
    """Handle analysis of a single file."""
    metadata = get_file_metadata(file_path)
    print(f"\nAnalyzing: {file_path}")
    print("-" * 40)
    print(f"File: {metadata['filename']}")
    print(f"Size: {metadata['size_human']}")
    print(f"Modified: {metadata['modified']}")
    
    print("\nContacting AI for analysis...")
    try:
        analysis, raw_json = analyze_single_file(file_path, read_file_content, get_file_metadata)
    except Exception as e:
        print(f"\nError: {str(e)}")
        print("\nPlease make sure:")
        print("1. GROQ_API_KEY environment variable is set")
        print("2. You have an active internet connection")
        print("3. Your Groq API key is valid")
        return
    
    if analysis is not None:
        print_single_analysis(analysis)
    else:
        print("Warning: Could not parse AI response as JSON. Showing raw output:")
        print(raw_json)
    
    # Save response
    try:
        saved_path = save_ai_response(file_path, raw_json)
        print(f"Analysis saved to: {saved_path}")
    except Exception as e:
        print(f"Warning: Could not save analysis: {str(e)}")


def _run_batch_mode(directory_path):
    """Handle batch analysis of all supported files in a directory, then enter query mode."""
    print(f"\nScanning: {directory_path}")
    files = scan_directory(directory_path)
    
    if not files:
        print("No supported files found.")
        return
    
    print(f"Found {len(files)} files")
    print()
    
    results = []
    errors = []
    total = len(files)
    
    print("Analyzing...")
    for i, file_path in enumerate(files, 1):
        filename = Path(file_path).name
        print_progress_bar(i, total, filename)
        
        try:
            analysis, raw_json = analyze_single_file(file_path, read_file_content, get_file_metadata)
            if analysis is not None:
                # Place filename prominently at the top for readability
                entry = {
                    "file": filename,
                    "path": file_path,
                }
                entry.update(analysis)
                results.append(entry)
            else:
                errors.append({"file": filename, "path": file_path, "error": "Failed to parse AI response"})
        except Exception as e:
            errors.append({"file": filename, "path": file_path, "error": str(e)})
    
    print()  # newline after progress bar
    
    # Print summary
    print_batch_summary(total, results, errors)
    
    # Save combined results to reports directory
    output_path = None
    try:
        output_path = save_batch_results(results, errors, directory_path, total)
        print(f"\nCombined results saved to: {output_path}")
    except Exception as e:
        print(f"Warning: Could not save combined results: {str(e)}")
    
    # Enter query mode
    if results:
        run_query_loop(results)
    else:
        print("\nNo files were analyzed successfully. Nothing to query.")


def _run_reports_mode(file_path):
    """Load a saved batch results file and enter query mode."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error loading reports file: {str(e)}")
        return
    
    results = data.get("results", [])
    print(f"\nLoaded {len(results)} results from: {file_path}")
    run_query_loop(results)


if __name__ == "__main__":
    main()