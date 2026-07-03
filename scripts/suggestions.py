"""
Filename and folder organization suggestions.

Provides AI-free suggestions based on analysis results, including
better filenames, folder reorganization ideas, and grouping proposals.
"""

from pathlib import Path
from typing import Optional
from collections import defaultdict

from scripts.categorization import get_category_icon


def suggest_filename(current_name: str, analysis: dict) -> Optional[str]:
    """
    Generate a suggested filename based on analysis and file metadata.
    Returns None if the current name seems reasonable.
    """
    suggested = analysis.get("suggested_filename", "")
    if suggested and suggested != current_name:
        return suggested
    return None


def suggest_folder_organization(results: list) -> dict:
    """
    Analyze a batch of results and suggest folder organization improvements.
    
    Returns dict with keys:
    - suggested_folders: dict of folder_name → [file entries]
    - splits: list of (category, count) where splitting would help
    - merges: list of (folder_a, folder_b) that could be merged
    """
    suggestions = {
        "suggested_folders": {},
        "splits": [],
        "merges": [],
        "summary": "",
    }
    
    if not results:
        return suggestions
    
    # Group by category
    by_category = defaultdict(list)
    for r in results:
        category = r.get("category", "Other") or "Other"
        by_category[category].append(r)
    
    # Suggest category-based folders
    for category, files in sorted(by_category.items(), key=lambda x: -len(x[1])):
        if len(files) >= 3:
            icon = get_category_icon(category)
            folder_name = f"{icon} {category}"
            suggestions["suggested_folders"][folder_name] = [
                f.get("file", "") for f in files
            ]
    
    # Detect folders that are too mixed (many categories in one directory)
    dir_categories = defaultdict(set)
    dir_counts = defaultdict(int)
    for r in results:
        path = r.get("path", "")
        parent = str(Path(path).parent) if path else "unknown"
        cat = r.get("category", "Other") or "Other"
        dir_categories[parent].add(cat)
        dir_counts[parent] += 1
    
    for directory, categories in sorted(dir_categories.items(), key=lambda x: -dir_counts[x[0]]):
        if len(categories) >= 4 and dir_counts[directory] >= 10:
            suggestions["splits"].append({
                "directory": directory,
                "categories": sorted(categories),
                "file_count": dir_counts[directory],
            })
    
    # Build summary
    folder_count = len(suggestions["suggested_folders"])
    split_count = len(suggestions["splits"])
    
    parts = []
    if folder_count:
        parts.append(f"{folder_count} category folders suggested")
    if split_count:
        parts.append(f"{split_count} directories could be split by category")
    
    suggestions["summary"] = ", ".join(parts) if parts else "No organization suggestions"
    
    return suggestions


def suggest_groups(results: list) -> dict:
    """
    Suggest logical groups for files based on project, category, and lifecycle.
    
    Returns: {group_name: [file entries]}
    """
    groups = defaultdict(list)
    
    for r in results:
        # Group by project first
        project = r.get("project", "") or ""
        if project:
            groups[f"📁 Project: {project}"].append(r)
            continue
        
        # Fallback: group by category + lifecycle
        category = r.get("category", "Other") or "Other"
        lifecycle = r.get("lifecycle", "") or ""
        if lifecycle:
            groups[f"{get_category_icon(category)} {category} ({lifecycle})"].append(r)
        else:
            groups[f"{get_category_icon(category)} {category}"].append(r)
    
    return dict(groups)


def get_cleanup_priority(results: list) -> list:
    """
    Rank files by how urgently they should be cleaned up.
    
    Higher priority = delete/archive sooner.
    Factors: action (Delete > Archive), confidence, lifecycle (Transient > Dormant),
    sentimental value (lower = more disposable).
    
    Returns sorted list of (priority_score, file_entry) tuples.
    """
    scored = []
    
    for r in results:
        score = 0
        
        action = r.get("action", "Keep")
        if action == "Delete":
            score += 80
        elif action == "Archive":
            score += 40
        elif action == "Review":
            score += 20
        
        # Lifecycle bonus
        lifecycle = r.get("lifecycle", "")
        if lifecycle == "Transient":
            score += 30
        elif lifecycle == "Dormant":
            score += 15
        
        # Confidence boost (more confident = more actionable)
        confidence = r.get("confidence", 50)
        score += confidence * 0.3
        
        # Sentimental value penalty (higher value = less likely to delete)
        sentimental = r.get("sentimental_value", 1)
        score -= sentimental * 8
        
        # Importance penalty
        importance = r.get("importance", 5)
        score -= importance * 3
        
        # Size bonus (larger files are more impactful to clean up)
        path = r.get("path", "")
        if path:
            try:
                size_mb = Path(path).stat().st_size / (1024 * 1024)
                if size_mb > 10:
                    score += 15
                elif size_mb > 1:
                    score += 5
            except OSError:
                pass
        
        scored.append((max(0, int(score)), r))
    
    scored.sort(key=lambda x: -x[0])
    return scored