"""
Plugin system foundation for AI File Manager.

Defines abstract base classes for extensibility:
- AnalysisPlugin: Per-file-type content extraction and metadata enrichment
- AIProvider: Alternative LLM providers (Ollama, OpenAI, Anthropic, etc.)
- PostProcessor: Post-analysis processing (auto-tagging, dedup, etc.)

Plugins live in a `plugins/` directory and are auto-discovered at startup.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Callable
import importlib.util
import inspect
import os


# ─── Plugin base classes ─────────────────────────────────────────────────────

class AnalysisPlugin(ABC):
    """
    Base class for file-type-specific analysis plugins.
    
    Override can_handle() and extract_content() to support new file types.
    Example: PDFPlugin, ImagePlugin, AudioPlugin, DOCXPlugin
    """
    
    @abstractmethod
    def can_handle(self, file_path: str) -> bool:
        """Return True if this plugin can handle the given file."""
        ...
    
    @abstractmethod
    def extract_content(self, file_path: str) -> str:
        """
        Extract text content from the file for AI analysis.
        Return a string representation of the file's content.
        """
        ...
    
    def get_metadata(self, file_path: str) -> dict:
        """
        Optionally return additional metadata about the file.
        Override to add plugin-specific metadata fields.
        """
        return {}
    
    @property
    def name(self) -> str:
        """Human-readable name for this plugin."""
        return self.__class__.__name__
    
    @property
    def supported_extensions(self) -> set:
        """Return set of file extensions this plugin supports."""
        return set()


class AIProvider(ABC):
    """
    Abstract base for AI providers.
    
    Implementations: GroqProvider, OllamaProvider, OpenAIProvider, AnthropicProvider
    """
    
    def __init__(self, model: str = ""):
        self.model = model
    
    @abstractmethod
    def analyze_file(self, file_path: str, read_content_fn, get_metadata_fn):
        """Analyze a single file. Returns (analysis_dict, raw_json_string)."""
        ...
    
    @abstractmethod
    def query(self, results: list, question: str) -> dict:
        """Query analysis results. Returns {"answer": ..., "matching_files": [...]}."""
        ...


class PostProcessor(ABC):
    """
    Post-analysis processor. Runs after each file is analyzed.
    
    Examples: Auto-tagger, duplicate detector, project grouper
    """
    
    @abstractmethod
    def process(self, analysis: dict, file_path: str) -> dict:
        """
        Process an analysis result and return (possibly modified) analysis dict.
        """
        return analysis


# ─── Plugin discovery ───────────────────────────────────────────────────────

PLUGIN_DIR = Path(__file__).resolve().parent.parent / "plugins"


def discover_plugins() -> dict:
    """
    Discover and load plugins from the plugins/ directory.
    
    Returns: {
        "analysis_plugins": [AnalysisPlugin instances],
        "post_processors": [PostProcessor instances],
    }
    """
    result = {
        "analysis_plugins": [],
        "post_processors": [],
    }
    
    if not PLUGIN_DIR.is_dir():
        return result
    
    for py_file in sorted(PLUGIN_DIR.glob("*.py")):
        if py_file.name.startswith("_"):
            continue
        
        try:
            module = _load_module(py_file)
            for name, obj in inspect.getmembers(module):
                if inspect.isclass(obj) and not obj.__name__.startswith("_"):
                    if issubclass(obj, AnalysisPlugin) and obj is not AnalysisPlugin:
                        result["analysis_plugins"].append(obj())
                    elif issubclass(obj, PostProcessor) and obj is not PostProcessor:
                        result["post_processors"].append(obj())
        except Exception as e:
            print(f"Warning: Failed to load plugin {py_file.name}: {e}")
    
    return result


def _load_module(py_file: Path):
    """Load a Python file as a module."""
    spec = importlib.util.spec_from_file_location(py_file.stem, py_file)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load {py_file}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module