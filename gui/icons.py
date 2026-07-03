"""
Icon constants for AI File Manager GUI.

Uses Unicode symbols and emoji for a clean, dependency-free icon set.
All icons are strings that can be used directly in labels and buttons.
"""

# ─── Action icons ────────────────────────────────────────────────────────────

KEEP = "✓"
DELETE = "✕"
ARCHIVE = "↓"
REVIEW = "⚠"
UNKNOWN = "?"

# ─── Status icons ────────────────────────────────────────────────────────────

SUCCESS = "✓"
ERROR = "✕"
WARNING = "⚠"
INFO = "ℹ"
PROGRESS = "⟳"
DONE = "✓"
CACHED = "⚡"

# ─── Navigation icons ────────────────────────────────────────────────────────

FOLDER = "📁"
FILE = "📄"
SEARCH = "🔍"
FILTER = "🔽"
SORT = "↕"
CLOSE = "✕"
MENU = "☰"
SETTINGS = "⚙"
DARK_MODE = "🌙"
LIGHT_MODE = "☀️"
REFRESH = "⟳"
EXPORT = "📤"
IMPORT = "📥"
TRASH = "🗑"
PIN = "📌"

# ─── Category icons (mirrors categorization.py) ──────────────────────────────

CATEGORY_ICONS = {
    "Programming": "💻",
    "Documents": "📄",
    "Finance": "💰",
    "School": "🎓",
    "Personal": "👤",
    "Media": "🎵",
    "Data": "📊",
    "Installer": "📦",
    "System": "⚙️",
    "Work": "💼",
    "Other": "📁",
}

# ─── Lifecycle icons ─────────────────────────────────────────────────────────

LIFECYCLE_ICONS = {
    "Active": "🟢",
    "Dormant": "🟡",
    "Archived": "🔵",
    "Transient": "⚪",
    "Unknown": "⚫",
}

# ─── Confidence icons ────────────────────────────────────────────────────────

CONFIDENCE_HIGH = "🟢"
CONFIDENCE_MEDIUM = "🟡"
CONFIDENCE_LOW = "🔴"

# ─── Dashboard icons ─────────────────────────────────────────────────────────

DASHBOARD = "📊"
FILES = "📄"
DUPLICATES = "📋"
TAGS = "🏷"
PROJECTS = "📁"
TIMELINE = "📅"
CHART = "📈"
CLEANUP = "🧹"
SUGGESTIONS = "💡"
HISTORY = "🕐"

# ─── Keyboard shortcut labels ────────────────────────────────────────────────

SHORTCUT_LABELS = {
    "scan_folder": "Ctrl+O",
    "scan_file": "Ctrl+N",
    "load_reports": "Ctrl+L",
    "query_focus": "Ctrl+F",
    "clear": "Ctrl+Shift+C",
    "dark_mode": "Ctrl+D",
    "export_csv": "Ctrl+E",
    "select_all": "Ctrl+A",
    "delete_marked": "Delete",
    "preview": "Space",
    "detail": "Enter",
    "refresh": "F5",
    "quit": "Ctrl+Q",
}


def get_category_icon(category: str) -> str:
    """Return the icon for a file category."""
    return CATEGORY_ICONS.get(category, "📁")


def get_lifecycle_icon(lifecycle: str) -> str:
    """Return the icon for a lifecycle state."""
    return LIFECYCLE_ICONS.get(lifecycle, "⚫")


def get_confidence_icon(confidence: int) -> str:
    """Return the icon for a confidence level."""
    if confidence >= 85:
        return CONFIDENCE_HIGH
    elif confidence >= 60:
        return CONFIDENCE_MEDIUM
    return CONFIDENCE_LOW


def get_action_icon(action: str) -> str:
    """Return the icon for a recommended action."""
    return {
        "Keep": KEEP,
        "Delete": DELETE,
        "Archive": ARCHIVE,
        "Review": REVIEW,
    }.get(action, UNKNOWN)