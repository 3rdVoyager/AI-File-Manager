#!/usr/bin/env python3
"""
AI File Manager - Main Entry Point

Analyzes files using an LLM (via Groq API) to classify, summarize, and recommend
actions (Keep/Delete/Archive/Review). Uses three strategic content snippets
(beginning, middle, end) from each file along with metadata for AI analysis.

Supports single-file analysis, batch folder analysis, and interactive query mode.

Usage:
    python main.py              # Interactive CLI
    python main.py --gui        # Launch GUI
"""

import os
import sys
import json
from pathlib import Path

from scripts.config import GROQ_API_KEY
from scripts.file_utils import get_file_metadata_dict, read_file_content, scan_directory
from scripts.analysis import analyze_file, scan_and_analyze
from scripts.ai_client import analyze_single_file
from scripts.reporter import (
    save_ai_response,
    save_batch_results,
    print_progress_bar,
    print_single_analysis,
    print_batch_summary,
)
from scripts.query_engine import run_query_loop
from scripts.cache import close as close_cache


def main():
    """Main entry point."""
    # Check for --gui flag
    if len(sys.argv) > 1 and sys.argv[1] == "--gui":
        _launch_gui()
        return

    if not GROQ_API_KEY:
        print("Error: GROQ_API_KEY not set.")
        print("Create a .env file with GROQ_API_KEY=your_api_key_here")
        print("Get a key from https://console.groq.com/keys")
        # Still allow GUI launch
        if len(sys.argv) > 1 and sys.argv[1] == "--gui":
            _launch_gui()
        return

    print("AI File Manager - Version 0.3")
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
    
    try:
        if is_reports:
            _run_reports_mode(resolved_path)
        elif is_folder:
            _run_batch_mode(resolved_path)
        else:
            _run_single_file_mode(resolved_path)
    finally:
        close_cache()


def _launch_gui():
    """Launch the graphical user interface."""
    try:
        import gui
        gui.main()
    except ImportError:
        print("Error: gui.py not found. Make sure it's in the project root.")
    except Exception as e:
        print(f"Error launching GUI: {e}")


def _run_single_file_mode(file_path):
    """Handle analysis of a single file."""
    metadata = get_file_metadata_dict(file_path)
    print(f"\nAnalyzing: {file_path}")
    print("-" * 40)
    print(f"File: {metadata['filename']}")
    print(f"Size: {metadata['size_human']}")
    
    print("\nContacting AI for analysis...")
    try:
        analysis, raw_json, was_cached = analyze_file(file_path)
    except Exception as e:
        print(f"\nError: {str(e)}")
        print("\nPlease make sure:")
        print("1. GROQ_API_KEY environment variable is set")
        print("2. You have an active internet connection")
        print("3. Your Groq API key is valid")
        return
    
    if analysis is not None:
        if was_cached:
            print("  (Cached result)")
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
    
    # Use the new pipeline
    results, errors, summary = scan_and_analyze(
        directory_path,
        on_file_complete=lambda i, total, fname: print_progress_bar(i, total, fname)
    )
    
    print()  # newline after progress bar
    
    # Print summary
    print(f"\n  Total files:   {summary.total_files}")
    print(f"  Analyzed:      {summary.analyzed}")
    print(f"  Cached:        {summary.cached}")
    print(f"  Errors:        {summary.errors}")
    print(f"  Duration:      {summary.duration_seconds:.1f}s")
    
    print()
    print("Actions recommended:")
    print(f"  {'Keep':<12} {summary.keep_count}")
    print(f"  {'Delete':<12} {summary.delete_count}")
    print(f"  {'Archive':<12} {summary.archive_count}")
    print(f"  {'Review':<12} {summary.review_count}")
    
    if errors:
        print()
        print("Errors:")
        for e in errors:
            print(f"  {Path(e['file']).name}: {e['error']}")
    
    # Convert AnalysisResult objects to dicts for query engine compatibility
    results_dicts = [r.to_dict() for r in results]
    
    # Save combined results
    output_path = None
    try:
        output_path = save_batch_results(results_dicts, errors, directory_path, total)
        print(f"\nResults saved to: {output_path}")
    except Exception as e:
        print(f"\nWarning: Could not save combined results: {str(e)}")
    
    # Enter query mode
    if results_dicts:
        run_query_loop(results_dicts)
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