#!/usr/bin/env python3
"""
AI File Manager - Main Entry Point

Analyzes files using an LLM (via Groq API) to classify, summarize, and recommend
actions (Keep/Delete/Archive). Sends three strategic content snippets (beginning,
middle, end) from each file along with metadata for AI analysis.

The AI returns structured JSON. The script parses it and displays a formatted
summary to the user, and saves the raw JSON to a .ai.txt file.

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
SNIPPET_START = 1500    # Characters from beginning
SNIPPET_MIDDLE = 1000   # Characters from middle
SNIPPET_END = 1500      # Characters from end
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
MODEL = "openai/gpt-oss-20b"  # Default model, can be overridden by .env


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

Return ONLY valid JSON with this exact structure (no markdown, no code fences, no extra text):
{{
  "summary": "One-sentence summary of the file content.",
  "category": "Document",
  "importance": 7,
  "action": "Keep",
  "confidence": 94,
  "reasoning": "Brief explanation for the recommendation.",
  "suggested_filename": "improved-filename.txt"
}}"""
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
                "content": "You are an expert file organization assistant. Analyze files and return structured JSON only. Be consistent and deterministic in your categorizations."
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
    """Save the AI response to a .ai.txt file."""
    input_path = Path(file_path)
    output_path = input_path.parent / f"{input_path.stem}.ai.txt"
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(ai_response)
    
    return str(output_path)


def main():
    """Main entry point."""
    print("AI File Manager - Version 0.1")
    print("=" * 40)
    
    # Get file path from user
    file_path = input("Enter the path to a file: ").strip()
    
    if not file_path:
        print("Error: No file path provided.")
        return
    
    # Remove surrounding quotes if present (from Copy as Path in Windows)
    file_path = file_path.strip('"').strip("'")
    
    # Replace single backslashes with forward slashes to avoid escape sequence issues
    file_path = file_path.replace('\\', '/')
    
    # Normalize path (handle Windows backslashes and convert to absolute path)
    file_path = os.path.abspath(os.path.normpath(file_path))
    
    # Check if file exists
    if not os.path.isfile(file_path):
        print(f"Error: File not found: {file_path}")
        print("\nTip: Use forward slashes (/) or double backslashes (\\\\) in Windows paths")
        print("Example: C:/Users/joshi/Downloads/test.txt or C:\\Users\\joshi\\Downloads\\test.txt")
        return
    
    print(f"\nAnalyzing: {file_path}")
    print("-" * 40)
    
    # Get metadata
    metadata = get_file_metadata(file_path)
    print(f"File: {metadata['filename']}")
    print(f"Size: {metadata['size_human']}")
    print(f"Modified: {metadata['modified']}")
    
    # Read content
    content = read_file_content(file_path)
    
    # Build prompt
    prompt = build_ai_prompt(metadata['filename'], metadata, content)
    
    # Call AI
    print("\nContacting AI for analysis...")
    try:
        ai_response = call_groq_api(prompt)
    except Exception as e:
        print(f"\nError: {str(e)}")
        print("\nPlease make sure:")
        print("1. GROQ_API_KEY environment variable is set")
        print("2. You have an active internet connection")
        print("3. Your Groq API key is valid")
        return
    
    # Parse and display JSON response
    print("\n" + "=" * 40)
    print("AI Analysis Result:")
    print("=" * 40)

    analysis = None
    try:
        analysis = json.loads(ai_response)
    except json.JSONDecodeError:
        print("Warning: Could not parse AI response as JSON. Showing raw output:")
        print(ai_response)

    if analysis is not None:
        print(f"  Summary:      {analysis.get('summary', 'N/A')}")
        print(f"  Category:     {analysis.get('category', 'N/A')}")
        print(f"  Importance:   {analysis.get('importance', 'N/A')}/10")
        print(f"  Action:       {analysis.get('action', 'N/A')}")
        print(f"  Confidence:   {analysis.get('confidence', 'N/A')}%")
        print(f"  Reasoning:    {analysis.get('reasoning', 'N/A')}")
        print(f"  Suggested:    {analysis.get('suggested_filename', 'N/A')}")
        print("=" * 40)

        # Save the raw JSON as-is, not the formatted display
        ai_response = json.dumps(analysis, indent=2)
    
    # Save response
    try:
        saved_path = save_ai_response(file_path, ai_response)
        print(f"\nAnalysis saved to: {saved_path}")
    except Exception as e:
        print(f"\nWarning: Could not save analysis: {str(e)}")


if __name__ == "__main__":
    main()
