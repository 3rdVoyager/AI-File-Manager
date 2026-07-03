"""
AI client: prompt construction, Groq API communication, response validation,
and retry logic.

Uses a structured schema approach to reduce hallucinations and ensure
consistent JSON output from the LLM.
"""

import json
import time
import httpx
from typing import Optional, Tuple

from scripts.config import (
    GROQ_API_KEY, MODEL, AI_TIMEOUT, AI_TEMPERATURE,
    AI_MAX_TOKENS, AI_RETRY_COUNT, AI_RETRY_DELAY
)


# ─── Schema for AI response validation ──────────────────────────────────────

REQUIRED_FIELDS = {"summary", "category", "subcategory", "action", "confidence"}
EXPECTED_TYPES = {
    "summary": str,
    "category": str,
    "subcategory": str,
    "action": str,
    "confidence": (int, float),
    "importance": (int, float),
    "lifecycle": str,
    "reasoning": str,
    "suggested_filename": str,
    "project": str,
    "tags": list,
    "sentimental_value": (int, float),
    "requires_review": bool,
}


# ─── System prompt ───────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are an expert file organization assistant. Your job is to analyze files and return structured JSON only.

RULES:
1. Return ONLY valid JSON — no markdown, no code fences, no extra text.
2. Be consistent and deterministic in your categorizations.
3. If the file content explicitly states what to do with it (e.g. "delete this file", "archive this"), follow that instruction.
4. When content is truncated, note the truncation in your reasoning and lower your confidence score.
5. Detect project names from file paths, directory structure, and file headers/comments.

CATEGORY HIERARCHY:
- Programming: Python, JavaScript, TypeScript, Java, C++, Go, Rust, HTML/CSS, Shell, SQL, Config, Other-Code
- Documents: Text, Markdown, PDF, Spreadsheet, Presentation, Notes, Report, Legal, Other-Doc
- Finance: Tax, Invoice, Receipt, Budget, Bank-Statement, Other-Finance
- School: Assignment, Notes, Research, Lecture, Transcript, Other-School
- Personal: Journal, Photo-Metadata, Contact, Health, Other-Personal
- Media: Image, Audio, Video, Font, Other-Media
- Data: CSV, JSON, XML, YAML, Database, Archive, Other-Data
- Installer: Setup, Package, Update, Driver, Other-Installer
- System: Log, Temp, Cache, Config, Backup, Other-System
- Work: Report, Email, Meeting-Notes, Project-Plan, Other-Work

TAGS: Generate tags using domain:value format. Common tags:
  project:<name> — detected project
  lifecycle:<active|dormant|archived|transient>
  type:<source|receipt|installer|screenshot|backup|config|asset|doc|temp|export>
  source:<user-created|downloaded|ai-generated|email-attachment|system>
  value:<sentimental|important|replaceable|critical>

Respond with this exact JSON structure:
{
  "summary": "One-sentence summary of the file content.",
  "category": "Programming",
  "subcategory": "Python",
  "project": "Detected project name or empty string",
  "tags": ["lifecycle:active", "type:source", "value:replaceable"],
  "importance": 5,
  "sentimental_value": 1,
  "lifecycle": "Active",
  "action": "Keep",
  "confidence": 90,
  "reasoning": "Brief explanation for the recommendation.",
  "suggested_filename": "",
  "requires_review": false
}"""


# ─── Prompt building ─────────────────────────────────────────────────────────

def build_analysis_prompt(file_path: str, metadata: dict, content: str) -> str:
    """Build the user prompt for file analysis."""
    prompt = f"""Analyze the following file and return ONLY valid JSON.

FILE INFORMATION:
- Filename: {metadata['filename']}
- Path: {metadata['path']}
- Size: {metadata.get('size_human', 'unknown')}
- Extension: {metadata.get('extension', 'unknown')}

FILE CONTENT:
{content}

Return ONLY valid JSON with the exact structure specified in the system prompt."""
    return prompt


def build_query_prompt(results: list, question: str) -> str:
    """Build a prompt that asks the AI to query a batch of analysis results."""
    results_json = json.dumps(results, indent=2)
    prompt = f"""You have a JSON array of analyzed files. Each entry contains analysis fields
like category, subcategory, project, lifecycle, action, importance, summary, tags, etc.

Answer the user's question by filtering, counting, or summarizing the data below.

Return ONLY valid JSON with no other text. The response must have this structure:
{{
  "answer": "A concise natural language answer to the user's question.",
  "matching_files": ["file1.txt", "file2.txt", ...]
}}

Include the filenames of any files that match the query in the matching_files array.
If the question is a general summary or count, matching_files can be empty.

USER QUESTION: {question}

ANALYSIS RESULTS:
{results_json}"""
    return prompt


# ─── API call ────────────────────────────────────────────────────────────────

def call_groq_api(prompt: str, system_message: Optional[str] = None) -> str:
    """Call the Groq API with the prompt and return the response text."""
    if not GROQ_API_KEY:
        raise ValueError(
            "GROQ_API_KEY not set. Create a .env file with GROQ_API_KEY=your_key"
        )
    
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    
    messages = []
    if system_message:
        messages.append({"role": "system", "content": system_message})
    messages.append({"role": "user", "content": prompt})
    
    payload = {
        "model": MODEL,
        "messages": messages,
        "temperature": AI_TEMPERATURE,
        "max_tokens": AI_MAX_TOKENS,
        "stream": False,
    }
    
    try:
        with httpx.Client(timeout=AI_TIMEOUT) as client:
            response = client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
    except httpx.TimeoutException:
        raise Exception("API request timed out. Check your internet connection.")
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 429:
            raise Exception("API rate limit exceeded. Please wait a moment and try again.")
        elif e.response.status_code == 401:
            raise Exception("Invalid API key. Check your GROQ_API_KEY in .env")
        raise Exception(f"API Error ({e.response.status_code}): {e.response.text}")
    except httpx.HTTPError as e:
        raise Exception(f"Network error: {str(e)}")
    except Exception as e:
        raise Exception(f"Error calling Groq API: {str(e)}")


# ─── Response validation ────────────────────────────────────────────────────

def validate_analysis_response(raw: str) -> Optional[dict]:
    """
    Validate and clean an AI analysis response.
    
    1. Attempts JSON parsing
    2. Checks required fields exist
    3. Coerces types
    4. Returns None if fundamentally invalid
    """
    # Try to parse JSON
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None
    
    if not isinstance(data, dict):
        return None
    
    # Check required fields
    for field in REQUIRED_FIELDS:
        if field not in data or data[field] is None or data[field] == "":
            # Don't fail immediately — fill missing required fields with defaults
            if field == "summary":
                data["summary"] = "No summary provided."
            elif field == "category":
                data["category"] = "Other"
            elif field == "subcategory":
                data["subcategory"] = "Other"
            elif field == "action":
                data["action"] = "Review"
            elif field == "confidence":
                data["confidence"] = 30
    
    # Coerce types for known fields
    for field, expected in EXPECTED_TYPES.items():
        if field in data and data[field] is not None:
            try:
                if expected == list and not isinstance(data[field], list):
                    data[field] = [str(data[field])]
                elif expected == bool:
                    data[field] = bool(data[field])
                elif isinstance(expected, tuple):
                    # Allow both int and float
                    data[field] = expected[0](data[field])
                else:
                    data[field] = expected(data[field])
            except (ValueError, TypeError):
                # If coercion fails, set default
                if field == "tags":
                    data[field] = []
                elif field == "requires_review":
                    data[field] = False
                elif field in ("importance", "sentimental_value", "confidence"):
                    data[field] = 0
    
    # Clamp numeric ranges
    data["confidence"] = max(0, min(100, int(data.get("confidence", 0))))
    data["importance"] = max(1, min(10, int(data.get("importance", 5))))
    data["sentimental_value"] = max(1, min(10, int(data.get("sentimental_value", 1))))
    
    # Validate action
    valid_actions = {"Keep", "Delete", "Archive", "Review"}
    if data.get("action") not in valid_actions:
        data["action"] = "Review"
    
    # Validate lifecycle
    valid_lifecycles = {"Active", "Dormant", "Archived", "Transient", "Unknown"}
    if data.get("lifecycle") not in valid_lifecycles:
        data["lifecycle"] = "Unknown"
    
    # Ensure tags is a list
    if not isinstance(data.get("tags"), list):
        data["tags"] = []
    
    # Derive requires_review
    if data.get("action") == "Review" or data.get("confidence", 100) < 60:
        data["requires_review"] = True
    
    return data


# ─── Main analysis function ──────────────────────────────────────────────────

def analyze_single_file(file_path: str, read_content_fn, get_metadata_fn) -> Tuple[Optional[dict], str]:
    """
    Analyze a single file and return (analysis_dict, raw_json_string).
    
    Features:
    - Retry logic (up to AI_RETRY_COUNT attempts)
    - Response validation + coercion
    - Timeout protection
    
    Returns (None, raw_text) if all retries fail.
    """
    content = read_content_fn(file_path)
    metadata = get_metadata_fn(file_path)
    
    # Use dict metadata for prompt compatibility
    if hasattr(metadata, "to_dict"):
        meta_dict = metadata.to_dict()
    else:
        meta_dict = metadata
    
    prompt = build_analysis_prompt(file_path, meta_dict, content)
    
    last_error = ""
    for attempt in range(AI_RETRY_COUNT + 1):
        try:
            ai_response = call_groq_api(prompt, system_message=SYSTEM_PROMPT)
            
            # Validate the response
            analysis = validate_analysis_response(ai_response)
            if analysis is not None:
                return analysis, json.dumps(analysis, indent=2)
            
            # If invalid, try again with error feedback
            if attempt < AI_RETRY_COUNT:
                prompt = (
                    f"Your previous response was not valid JSON. "
                    f"Please return ONLY valid JSON following the exact structure provided.\n\n"
                    f"Original file:\n{content[:500]}"
                )
                time.sleep(AI_RETRY_DELAY)
                continue
            
            last_error = "Failed to parse AI response as valid JSON after retries"
        except Exception as e:
            last_error = str(e)
            if attempt < AI_RETRY_COUNT:
                time.sleep(AI_RETRY_DELAY)
                continue
    
    # All retries exhausted
    return None, last_error


# ─── Provider abstraction (prepares for local LLM support) ──────────────────

class AIProvider:
    """Abstract base for AI providers. Currently wraps Groq, but enables future
    local LLM support (Ollama, llama.cpp, etc.) with the same interface."""
    
    def __init__(self, model: str = MODEL):
        self.model = model
    
    def analyze_file(self, file_path: str, read_content_fn, get_metadata_fn) -> Tuple[Optional[dict], str]:
        """Analyze a single file. Drop-in for analyze_single_file."""
        return analyze_single_file(file_path, read_content_fn, get_metadata_fn)
    
    def query(self, results: list, question: str) -> dict:
        """Run a natural-language query against analysis results."""
        from scripts.query_engine import query_results
        return query_results(results, question)