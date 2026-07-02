"""
Query engine: interactive natural-language querying of batch analysis results.
"""

import json

from scripts.ai_client import build_query_prompt, call_groq_api


def query_results(results, question):
    """Send a natural-language question about the batch results to the AI.
    
    Returns a dict with "answer" and "matching_files" keys.
    """
    if not results:
        return {"answer": "No results to query.", "matching_files": []}

    prompt = build_query_prompt(results, question)
    
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


def run_query_loop(results):
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