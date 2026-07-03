"""
Query engine: interactive natural-language querying of batch analysis results,
plus structured keyword-based filtering for the GUI.
"""

import json
from typing import Optional

from scripts.ai_client import build_query_prompt, call_groq_api


def query_results(results: list, question: str) -> dict:
    """
    Send a natural-language question about the batch results to the AI.
    
    Returns a dict with "answer" and "matching_files" keys.
    """
    if not results:
        return {"answer": "No results to query.", "matching_files": []}

    # Convert AnalysisResult objects to dicts if needed
    results_data = []
    for r in results:
        if hasattr(r, "to_dict"):
            results_data.append(r.to_dict())
        else:
            results_data.append(r)

    prompt = build_query_prompt(results_data, question)
    
    system = (
        "You are a data analysis assistant. Given a JSON array of file analysis results, "
        "answer the user's question by filtering, counting, or summarizing the data. "
        "Return ONLY valid JSON. Be precise and concise."
    )
    
    try:
        ai_response = call_groq_api(prompt, system_message=system)
        response = json.loads(ai_response)
        return response
    except json.JSONDecodeError:
        return {
            "answer": "Sorry, I couldn't process that query. Please try rephrasing.",
            "matching_files": []
        }
    except Exception as e:
        return {
            "answer": f"Error querying results: {str(e)}",
            "matching_files": []
        }


def keyword_filter(results: list, **filters) -> list:
    """
    Filter results by field values without an AI call.
    
    Usage:
        keyword_filter(results, category="Programming", action="Keep")
        keyword_filter(results, confidence_min=80, lifecycle="Active")
    
    Returns filtered list.
    """
    filtered = results
    
    for key, value in filters.items():
        if key.endswith("_min") or key.endswith("_max"):
            continue  # handle numeric filters separately
        
        if key in ("category", "subcategory", "action", "lifecycle", "project"):
            filtered = [r for r in filtered if str(r.get(key, "")).lower() == str(value).lower()]
    
    # Numeric filters
    if "confidence_min" in filters:
        filtered = [r for r in filtered if r.get("confidence", 0) >= filters["confidence_min"]]
    if "confidence_max" in filters:
        filtered = [r for r in filtered if r.get("confidence", 100) <= filters["confidence_max"]]
    if "importance_min" in filters:
        filtered = [r for r in filtered if r.get("importance", 0) >= filters["importance_min"]]
    
    # Tag filter
    if "tag" in filters:
        tag_value = filters["tag"].lower()
        filtered = [
            r for r in filtered
            if any(tag_value in t.lower() for t in r.get("tags", []))
        ]
    
    # Search in summary/filename
    if "search" in filters:
        query = filters["search"].lower()
        filtered = [
            r for r in filtered
            if query in str(r.get("file", "")).lower()
            or query in str(r.get("summary", "")).lower()
            or query in str(r.get("reasoning", "")).lower()
        ]
    
    return filtered


def get_safe_to_delete(results: list, min_confidence: int = 70) -> list:
    """Return files that are probably safe to delete."""
    return keyword_filter(
        results, action="Delete", confidence_min=min_confidence
    )


def run_query_loop(results: list):
    """Interactive loop: repeatedly ask the user for queries until they exit."""
    if not results:
        print("\nNo results loaded. Nothing to query.")
        return

    print("\n" + "=" * 40)
    print("Query Mode")
    print("=" * 40)
    print("Ask questions about the analyzed files.")
    print("Examples:")
    print('  "Show me all inactive programming projects"')
    print('  "Find documents related to taxes"')
    print('  "What should I delete?"')
    print('  "How many Python files do I have?"')
    print('  "List all installers"')
    print('  "exit" to quit')
    print("=" * 40)

    while True:
        try:
            question = input("\nQuery: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not question:
            continue
        if question.lower() in ("exit", "quit", "q"):
            break

        print("  Thinking...", end="", flush=True)
        response = query_results(results, question)
        print("\r" + " " * 40, end="\r", flush=True)

        print(f"\n{response.get('answer', 'No answer.')}")

        matches = response.get("matching_files", [])
        if matches:
            print()
            for fname in matches:
                print(f"  • {fname}")

    print("\nExited query mode.")