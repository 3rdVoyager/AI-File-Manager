#!/usr/bin/env python3
"""
AI File Manager - Main Entry Point

Analyzes files using an LLM (via Groq API) to classify, summarize, and recommend
actions (Keep/Delete/Archive). Sends three strategic content snippets (beginning,
middle, end) from each file along with metadata for AI analysis.

Supports single-file analysis (`python main.py` then enter a path) and batch
folder analysis (`python main.py` then enter `folder:C:/path/to/folder`).

The AI returns structured JSON. The script parses it and displays a formatted
summary to the user, and saves the raw JSON to the reports/ directory.

Before running make sure to run `pip install -r requirements.txt` to install dependencies.
Run with: python main.py
"""

import os
import json
from pathlib import Path
from datetime import datetime

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

# Configuration
SNIPPET_START = 1000    # Characters from beginning
SNIPPET_MIDDLE = 1000   # Characters from middle
SNIPPET_END = 1000      # Characters from end
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
MODEL = "openai/gpt-oss-20b"  # Default model, can be overridden by .env

# Reports directory (relative to this script)
REPORTS_DIR = Path(__file__).parent / "reports"


def get_reports_dir():
    """Ensure the reports directory exists and return its path."""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    return REPORTS_DIR


def get_file_metadata(file_path):
    """Extract metadata from a file."""
    path = Path(file_path)
    stat = path.stat()
    
    return {
        "filename": path.name,
        "path": str(path),
        "size_bytes": stat.st_size,
        "size_human": format_size(stat.st_size),
        "created": datetime.fromtimestamp(stat.st_ctime).strftime("%Y-%m-%d %H:%M:%S"),
        "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
        "extension": path.suffix.lower() if path.suffix else "none",
    }


def format_size(size_bytes):
    """Format file size in human-readable format."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.2f} TB"


def read_file_content(file_path):
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


def get_supported_extensions():
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


def scan_directory(directory_path):
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
        if file_path.suffix.lower() in supported:
            files.append(str(file_path))
    
    return files


def build_ai_prompt(filename, metadata, content):
    """Build the prompt to send to the AI."""
    prompt = f"""Analyze the following file and return ONLY valid JSON with no other text.

FILE INFORMATION:
- Filename: {metadata['filename']}
- Path: {metadata['path']}
- Size: {metadata['size_human']}
- Created: {metadata['created']}
- Modified: {metadata['modified']}
- Extension: {metadata['extension']}

FILE CONTENT:
{content}

IMPORTANT: If the file content explicitly states what should be done with it
(e.g. "this file should be deleted", "archive this", "keep this"), follow that
instruction. Otherwise, use your best judgment based on the content.

Return ONLY valid JSON with this exact structure (no markdown, no code fences, no extra text):
{{
  "summary": "One-sentence summary of the file content.",
  "category": "Document",
  "importance": 7,
  "action": "Keep",
  "confidence": 94,
  "reasoning": "Brief explanation for the recommendation.",
  "suggested_filename": "improved-filename.txt"
}}

Possible values for "action": "Keep", "Delete", or "Archive"."""
    return prompt


def call_groq_api(prompt):
    """Call the Groq API with the prompt."""
    import httpx
    
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY environment variable not set")
    
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    
    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "system",
                "content": "You are an expert file organization assistant. Analyze files and return structured JSON only. Be consistent and deterministic in your categorizations. Follow any explicit instructions found in the file content about whether to keep, delete, or archive the file."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.2,
        "max_tokens": 2000,
        "stream": False,
    }
    
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
    except httpx.HTTPError as e:
        raise Exception(f"API Error: {str(e)}")
    except Exception as e:
        raise Exception(f"Error calling Groq API: {str(e)}")


def save_ai_response(file_path, ai_response):
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


def analyze_single_file(file_path):
    """Analyze a single file and return the parsed analysis dict and raw JSON string."""
    content = read_file_content(file_path)
    metadata = get_file_metadata(file_path)
    prompt = build_ai_prompt(metadata["filename"], metadata, content)
    ai_response = call_groq_api(prompt)
    
    try:
        analysis = json.loads(ai_response)
        return analysis, json.dumps(analysis, indent=2)
    except json.JSONDecodeError:
        return None, ai_response


def print_progress_bar(current, total, filename, bar_width=20):
    """Print a single-line progress bar with filename."""
    filled = int(bar_width * current / total)
    bar = "█" * filled + "░" * (bar_width - filled)
    # Truncate long filenames to fit terminal width (~80 chars)
    name = filename if len(filename) <= 40 else "..." + filename[-37:]
    print(f"\r  [{bar}] {current}/{total}  {name:<40}", end="", flush=True)


def print_single_analysis(analysis):
    """Print a parsed analysis dict in human-readable format."""
    print("=" * 40)
    print("AI Analysis Result:")
    print("=" * 40)
    print(f"  Summary:      {analysis.get('summary', 'N/A')}")
    print(f"  Category:     {analysis.get('category', 'N/A')}")
    print(f"  Importance:   {analysis.get('importance', 'N/A')}/10")
    print(f"  Action:       {analysis.get('action', 'N/A')}")
    print(f"  Confidence:   {analysis.get('confidence', 'N/A')}%")
    print(f"  Reasoning:    {analysis.get('reasoning', 'N/A')}")
    print(f"  Suggested:    {analysis.get('suggested_filename', 'N/A')}")
    print("=" * 40)


def main():
    """Main entry point."""
    print("AI File Manager - Version 0.2")
    print("=" * 40)
    
    # Get input from user
    user_input = input("Enter the path to a file (or folder:path): ").strip()
    
    if not user_input:
        print("Error: No input provided.")
        return
    
    # Remove surrounding quotes if present
    user_input = user_input.strip('"').strip("'")
    
    # Detect folder mode
    is_folder = user_input.lower().startswith("folder:")
    if is_folder:
        raw_path = user_input[7:].strip().strip('"').strip("'")
    else:
        raw_path = user_input
    
    # Normalize path
    raw_path = raw_path.replace('\\', '/')
    resolved_path = os.path.abspath(os.path.normpath(raw_path))
    
    if is_folder:
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
        analysis, raw_json = analyze_single_file(file_path)
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
    """Handle batch analysis of all supported files in a directory."""
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
            analysis, raw_json = analyze_single_file(file_path)
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
    
    # Save combined results to reports directory
    output = {
        "analysis_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "directory": directory_path,
        "total_files": total,
        "analyzed": len(results),
        "errors": len(errors),
        "results": results,
        "error_details": errors,
    }
    
    source_dir_name = Path(directory_path).name or "root"
    reports_dir = get_reports_dir()
    output_path = reports_dir / f"batch_{source_dir_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2)
        print(f"\nCombined results saved to: {output_path}")
    except Exception as e:
        print(f"Warning: Could not save combined results: {str(e)}")


if __name__ == "__main__":
    main()