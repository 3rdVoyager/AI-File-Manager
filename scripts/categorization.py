"""
Categorization system: tag taxonomy, category hierarchy, and utility functions
for working with tags and categories in analysis results.

Provides client-side tag inference (without AI calls) for common patterns
like screenshot detection, installer detection, and project name extraction
from file paths.
"""

import re
from pathlib import Path
from typing import Optional

from scripts.models import TAG_PROJECT, TAG_LIFECYCLE, TAG_TYPE, TAG_SOURCE, TAG_VALUE


# ─── Category hierarchy ──────────────────────────────────────────────────────

CATEGORY_HIERARCHY = {
    "Programming": {
        "icon": "💻",
        "subcategories": [
            "Python", "JavaScript", "TypeScript", "Java", "C++", "C", "Go",
            "Rust", "Ruby", "PHP", "Swift", "Kotlin", "HTML/CSS", "Shell",
            "SQL", "Config", "Other-Code"
        ],
    },
    "Documents": {
        "icon": "📄",
        "subcategories": [
            "Text", "Markdown", "PDF", "Spreadsheet", "Presentation",
            "Notes", "Report", "Legal", "Other-Doc"
        ],
    },
    "Finance": {
        "icon": "💰",
        "subcategories": [
            "Tax", "Invoice", "Receipt", "Budget", "Bank-Statement", "Other-Finance"
        ],
    },
    "School": {
        "icon": "🎓",
        "subcategories": [
            "Assignment", "Notes", "Research", "Lecture", "Transcript", "Other-School"
        ],
    },
    "Personal": {
        "icon": "👤",
        "subcategories": [
            "Journal", "Photo-Metadata", "Contact", "Health", "Other-Personal"
        ],
    },
    "Media": {
        "icon": "🎵",
        "subcategories": [
            "Image", "Audio", "Video", "Font", "Other-Media"
        ],
    },
    "Data": {
        "icon": "📊",
        "subcategories": [
            "CSV", "JSON", "XML", "YAML", "Database", "Archive", "Other-Data"
        ],
    },
    "Installer": {
        "icon": "📦",
        "subcategories": [
            "Setup", "Package", "Update", "Driver", "Other-Installer"
        ],
    },
    "System": {
        "icon": "⚙️",
        "subcategories": [
            "Log", "Temp", "Cache", "Config", "Backup", "Other-System"
        ],
    },
    "Work": {
        "icon": "💼",
        "subcategories": [
            "Report", "Email", "Meeting-Notes", "Project-Plan", "Other-Work"
        ],
    },
    "Other": {
        "icon": "📁",
        "subcategories": ["Other"],
    },
}


# ─── Client-side tag inference ──────────────────────────────────────────────

# Patterns for detecting file types from filenames
SCREENSHOT_PATTERNS = [
    re.compile(r"screenshot", re.IGNORECASE),
    re.compile(r"screen.?shot", re.IGNORECASE),
    re.compile(r"screen.?capture", re.IGNORECASE),
    re.compile(r"snip", re.IGNORECASE),
    re.compile(r"^Screenshot_\d{4}", re.IGNORECASE),
]

INSTALLER_PATTERNS = [
    re.compile(r"\.(exe|msi|dmg|pkg|deb|rpm|AppImage)$", re.IGNORECASE),
    re.compile(r"(install|setup|update)", re.IGNORECASE),
]

DOWNLOAD_PATTERNS = [
    re.compile(r"^download", re.IGNORECASE),
    re.compile(r"\.(crdownload|part)$", re.IGNORECASE),
]

TEMP_PATTERNS = [
    re.compile(r"^~", re.IGNORECASE),
    re.compile(r"\.(tmp|temp|swp|bak|old)$", re.IGNORECASE),
]

BACKUP_PATTERNS = [
    re.compile(r"(backup|\.bak|\.old)", re.IGNORECASE),
]

PROJECT_NAME_PATTERNS = [
    # Detect project names from path segments (common patterns)
    re.compile(r"projects?[\\/]([^\\/]+)", re.IGNORECASE),
    re.compile(r"workspace[\\/]([^\\/]+)", re.IGNORECASE),
    re.compile(r"repos?[\\/]([^\\/]+)", re.IGNORECASE),
    re.compile(r"src[\\/]([^\\/]+)", re.IGNORECASE),
]


def infer_tags_from_filename(file_path: str) -> list:
    """
    Infer tags from filename and path without an AI call.
    Returns a list of tag strings.
    """
    tags = []
    path = Path(file_path)
    filename = path.name
    ext = path.suffix.lower()
    
    # Type detection
    if any(p.search(filename) for p in SCREENSHOT_PATTERNS):
        tags.append(TAG_TYPE.format("screenshot"))
    
    if any(p.search(filename) for p in INSTALLER_PATTERNS) or ext in (".exe", ".msi", ".dmg", ".pkg", ".deb", ".rpm"):
        tags.append(TAG_TYPE.format("installer"))
    
    if any(p.search(filename) for p in DOWNLOAD_PATTERNS):
        tags.append(TAG_SOURCE.format("downloaded"))
    
    if any(p.search(filename) for p in TEMP_PATTERNS):
        tags.append(TAG_LIFECYCLE.format("transient"))
        tags.append(TAG_TYPE.format("temp"))
    
    if any(p.search(filename) for p in BACKUP_PATTERNS):
        tags.append(TAG_TYPE.format("backup"))
    
    # Source detection from path
    path_str = str(path).lower()
    if "download" in path_str:
        tags.append(TAG_SOURCE.format("downloaded"))
    if "temp" in path_str or "tmp" in path_str:
        tags.append(TAG_TYPE.format("temp"))
    
    # Project detection from path
    project = infer_project_name(file_path)
    if project:
        tags.append(TAG_PROJECT.format(project))
    
    return tags


def infer_project_name(file_path: str) -> Optional[str]:
    """
    Try to infer a project name from the file path.
    Looks for common project directory patterns.
    """
    path_str = str(Path(file_path))
    
    for pattern in PROJECT_NAME_PATTERNS:
        match = pattern.search(path_str)
        if match:
            name = match.group(1)
            # Clean up common suffixes
            name = re.sub(r"[-_\s]+$", "", name)
            if name and len(name) < 60:
                return name
    
    # Fallback: use parent directory name if it looks like a project
    parent = Path(file_path).parent.name
    if parent and parent not in ("src", "lib", "bin", "dist", "build", "node_modules"):
        # Check if parent looks like a project (not too generic)
        generic = {"desktop", "documents", "downloads", "home", "root", "users"}
        if parent.lower() not in generic:
            return parent
    
    return None


def get_category_icon(category: str) -> str:
    """Return the emoji icon for a category."""
    info = CATEGORY_HIERARCHY.get(category)
    if info:
        return info["icon"]
    return "📁"


def get_all_categories() -> list:
    """Return sorted list of all category names."""
    return sorted(CATEGORY_HIERARCHY.keys())


def get_subcategories(category: str) -> list:
    """Return subcategories for a given category."""
    info = CATEGORY_HIERARCHY.get(category)
    if info:
        return info["subcategories"]
    return []


def format_tags_display(tags: list) -> str:
    """Format tags for display (e.g., in a tooltip or detail view)."""
    if not tags:
        return "No tags"
    return "  ".join(tags)


def tag_to_display(tag: str) -> str:
    """Convert a tag like 'lifecycle:active' to a display string 'Active'."""
    if ":" in tag:
        return tag.split(":", 1)[1].replace("-", " ").title()
    return tag.replace("-", " ").title()