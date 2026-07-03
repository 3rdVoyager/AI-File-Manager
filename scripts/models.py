"""
Data models for AI File Manager.

Typed dataclasses representing analysis results, file metadata,
and aggregation data used throughout the application.
"""

from dataclasses import dataclass, field, asdict
from typing import Optional
from datetime import datetime


# ─── Standard Tags ───────────────────────────────────────────────────────────

# Tag namespaces: domain:value
# Tags are always lowercase strings with a colon separator

TAG_PROJECT = "project:{}"        # project:ai-file-manager
TAG_LIFECYCLE = "lifecycle:{}"    # lifecycle:active
TAG_TYPE = "type:{}"              # type:source | type:receipt | type:screenshot
TAG_SOURCE = "source:{}"          # source:downloaded | source:user-created
TAG_VALUE = "value:{}"            # value:sentimental | value:replaceable
TAG_ACTION = "action:{}"          # action:keep | action:delete


# ─── Enums / Constants ──────────────────────────────────────────────────────

VALID_ACTIONS = {"Keep", "Delete", "Archive", "Review"}
VALID_LIFECYCLES = {"Active", "Dormant", "Archived", "Transient", "Unknown"}


@dataclass
class FileMetadata:
    """Structured file metadata extracted from the filesystem."""
    filename: str
    path: str
    size_bytes: int
    size_human: str
    created: str
    modified: str
    extension: str
    content_hash: str = ""


@dataclass
class AnalysisResult:
    """
    Complete analysis result for a single file.
    All fields are optional so partial/incomplete AI responses are safe.
    """
    # Identity
    file: str = ""
    path: str = ""
    
    # Classification
    summary: str = ""
    category: str = ""
    subcategory: str = ""
    tags: list = field(default_factory=list)
    project: str = ""
    
    # Scoring
    importance: int = 5
    sentimental_value: int = 1
    confidence: int = 50
    
    # Lifecycle & action
    lifecycle: str = "Unknown"
    action: str = "Review"
    
    # Reasoning
    reasoning: str = ""
    suggested_filename: str = ""
    requires_review: bool = False
    
    # Advanced
    duplicate_group: str = ""
    duplicate_of: list = field(default_factory=list)
    
    def to_dict(self) -> dict:
        """Serialize to a plain dict for JSON output."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> "AnalysisResult":
        """Create from a dict (e.g., parsed JSON from AI or cache)."""
        # Filter to only known fields to avoid errors
        known = {k: v for k, v in data.items() if k in cls.__annotations__}
        return cls(**known)


@dataclass
class BatchSummary:
    """Aggregated summary of a batch scan."""
    total_files: int = 0
    analyzed: int = 0
    errors: int = 0
    cached: int = 0
    new_files: int = 0
    
    # Action counts
    keep_count: int = 0
    delete_count: int = 0
    archive_count: int = 0
    review_count: int = 0
    
    # Category breakdown
    categories: dict = field(default_factory=dict)
    
    # Lifecycle breakdown
    lifecycle_counts: dict = field(default_factory=dict)
    
    # Confidence distribution
    confidence_low: int = 0    # < 60
    confidence_medium: int = 0 # 60-85
    confidence_high: int = 0   # > 85
    
    # Projects detected
    projects: dict = field(default_factory=dict)
    
    # Duplicates
    duplicate_candidates: int = 0
    
    # Largest files (top 10 by size)
    largest_files: list = field(default_factory=list)
    
    # Review queue
    needs_review: list = field(default_factory=list)
    
    # Scan info
    scan_date: str = ""
    directory: str = ""
    duration_seconds: float = 0.0


@dataclass
class ScanProgress:
    """Tracks progress of an active scan for UI updates."""
    current: int = 0
    total: int = 0
    current_file: str = ""
    status: str = "idle"  # idle | scanning | analyzing | done | error
    scanned: int = 0
    cached: int = 0
    errors: int = 0
    elapsed_seconds: float = 0.0