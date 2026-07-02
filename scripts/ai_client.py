"""
AI client: prompt construction and Groq API communication.
"""

import json

from scripts.config import GROQ_API_KEY, MODEL


def build_ai_prompt(filename, metadata, content):
    """Build the prompt to send to the AI for file analysis."""
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
  "category": "Programming",
  "subcategory": "Python",
  "project": "AI File Manager",
  "importance": 8,
  "lifecycle": "Active",
  "action": "Keep",
  "confidence": 95,
  "reasoning": "Brief explanation for the recommendation.",
  "suggested_filename": "improved-filename.txt"
}}

Field guidelines:
- category: One of Programming, Document, Image, Audio, Video, Archive, Data, Config, School, Work, Personal, Finance, Installer, Other
- subcategory: More specific (e.g. Python, JavaScript, PDF, Spreadsheet, Tax, Invoice, Photo, etc.)
- project: The project or context this file belongs to, or null if unknown
- lifecycle: One of Active, Stale, Archive, Deprecated, Transient
- action: One of Keep, Delete, Archive
- confidence: 0-100 integer
- importance: 1-10 integer"""
    return prompt


def build_query_prompt(results, question):
    """Build a prompt that asks the AI to query a batch of analysis results."""
    results_json = json.dumps(results, indent=2)
    prompt = f"""You have a JSON array of analyzed files. Each entry contains analysis fields
like category, subcategory, project, lifecycle, action, importance, summary, etc.

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


def call_groq_api(prompt, system_message=None):
    """Call the Groq API with the prompt and return the response text."""
    import httpx
    
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY environment variable not set")
    
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


def analyze_single_file(file_path, read_file_content_fn, get_file_metadata_fn):
    """Analyze a single file and return (analysis_dict, pretty_json_string).
    
    You must pass in the read_file_content and get_file_metadata functions
    from file_utils to avoid circular imports at module level.
    """
    content = read_file_content_fn(file_path)
    metadata = get_file_metadata_fn(file_path)
    prompt = build_ai_prompt(metadata["filename"], metadata, content)
    
    system = "You are an expert file organization assistant. Analyze files and return structured JSON only. Be consistent and deterministic in your categorizations. Follow any explicit instructions found in the file content about whether to keep, delete, or archive the file."
    
    ai_response = call_groq_api(prompt, system_message=system)
    
    try:
        analysis = json.loads(ai_response)
        return analysis, json.dumps(analysis, indent=2)
    except json.JSONDecodeError:
        return None, ai_response