#!/usr/bin/env python3
"""
AI File Manager - Main Entry Point

This script is the main script for the AI-File-Manager project. It should be run
from the command line and receive an input file path from the user. It will then
send a few snippets of the content, the file name, and any metadata to a free, fast
AI model for processing (Groq).

The AI model will then return a response which will be printed to the console
with the following information:
1. One-sentence summary
2. Category
3. Importance (1-10)
4. Keep/Delete/Archive
5. Confidence (0-100%)
6. Reasoning
7. Suggested filename

Output will be in Markdown format for easy reading and copying. The script will
also save the AI response to a text file in the same directory as the input file,
with the same name as the input file but with a .ai.txt extension.


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
MAX_CONTENT_LENGTH = 4000  # Max characters to send to the AI
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


def read_file_content(file_path, max_length=MAX_CONTENT_LENGTH):
    """Read file content and truncate if necessary."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Truncate if too long, keeping the beginning
        if len(content) > max_length:
            content = content[:max_length] + "\n\n... [Content truncated]"
        
        return content
    except UnicodeDecodeError:
        # Try with different encodings
        try:
            with open(file_path, "r", encoding="latin-1") as f:
                content = f.read()
            return content[:max_length] + ("\n\n... [Content truncated]" if len(content) > max_length else "")
        except Exception as e:
            return f"[Error reading file: {str(e)}]"
    except Exception as e:
        return f"[Error reading file: {str(e)}]"


def build_ai_prompt(filename, metadata, content):
    """Build the prompt to send to the AI."""
    prompt = f"""You are a helpful AI assistant analyzing files for organization.

Analyze the following file and provide a structured response in Markdown format.

FILE INFORMATION:
- Filename: {metadata['filename']}
- Path: {metadata['path']}
- Size: {metadata['size_human']}
- Created: {metadata['created']}
- Modified: {metadata['modified']}
- Extension: {metadata['extension']}

FILE CONTENT (first {min(len(content), MAX_CONTENT_LENGTH)} characters):
{content}

Please provide your analysis in the following Markdown format:

# File Analysis: {metadata['filename']}

## Summary
[One-sentence summary of the file content]

## Category
[Category such as: Document, Code, Image, Archive, School, Work, Personal, etc.]

## Importance
[Rating from 1-10 where 1 is least important and 10 is most important]

## Action
[One of: Keep, Delete, Archive]

## Confidence
[Percentage from 0-100% indicating confidence in the recommendation]

## Reasoning
[Brief explanation for the recommendation]

## Suggested Filename
[Improved filename suggestion, or keep current if appropriate]

Be concise but thorough in your reasoning."""
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
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
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
    
    # Print response
    print("\n" + "=" * 40)
    print("AI Analysis Result:")
    print("=" * 40)
    print(ai_response)
    print("=" * 40)
    
    # Save response
    try:
        saved_path = save_ai_response(file_path, ai_response)
        print(f"\nAnalysis saved to: {saved_path}")
    except Exception as e:
        print(f"\nWarning: Could not save analysis: {str(e)}")


if __name__ == "__main__":
    main()
