"""
Detail panel for AI File Manager GUI.

Shows full file details, analysis results, tags, and a preview
of the file content when a file is selected.
"""

import json
import tkinter as tk
from tkinter import ttk
from pathlib import Path
from typing import Optional

from gui.theme import ThemeManager
from gui.icons import (
    get_action_icon, get_category_icon, get_confidence_icon,
    get_lifecycle_icon
)
from gui.widgets import CardFrame


class DetailPanel(ttk.Frame):
    """
    Right-side detail panel showing file information.
    
    Shows:
    - File metadata (name, path, size, modified)
    - AI analysis results (summary, category, action, confidence)
    - Tags list
    - Raw analysis JSON
    - File content preview (for text files)
    """

    def __init__(self, parent, theme: ThemeManager):
        super().__init__(parent, style="Panel.TFrame", width=350)
        self.theme = theme
        self._current_entry = None
        self.pack_propagate(False)
        
        self._build_ui()
        self._show_empty()

    def _build_ui(self):
        """Construct the detail panel layout."""
        # Header
        self.header_frame = ttk.Frame(self, style="Panel.TFrame")
        self.header_frame.pack(fill=tk.X, padx=12, pady=(12, 4))
        
        self.file_icon_label = ttk.Label(self.header_frame, text="📄",
                                        font=("Segoe UI", 20))
        self.file_icon_label.pack(side=tk.LEFT, padx=(0, 8))
        
        self.file_name_label = ttk.Label(self.header_frame, text="",
                                        style="Heading.TLabel",
                                        font=("Segoe UI", 12, "bold"),
                                        wraplength=300)
        self.file_name_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Separator
        ttk.Separator(self, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=8, pady=4)
        
        # Scrollable content
        canvas = tk.Canvas(self, bg=self.theme.colors["panel_bg"],
                          highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=canvas.yview)
        self.scroll_frame = ttk.Frame(canvas, style="Panel.TFrame")
        
        self.scroll_frame.bind("<Configure>",
                              lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # ── Metadata section ──
        self.meta_card = CardFrame(self.scroll_frame, self.theme, "📋 File Info")
        self.meta_card.pack(fill=tk.X, padx=8, pady=4)
        self.meta_content = self.meta_card.content
        
        self.meta_labels = {}
        meta_fields = [
            ("path", "Path:"),
            ("size", "Size:"),
            ("extension", "Type:"),
            ("modified", "Modified:"),
        ]
        for key, label in meta_fields:
            row = ttk.Frame(self.meta_content, style="Card.TFrame")
            row.pack(fill=tk.X, pady=1)
            ttk.Label(row, text=label, style="Card.TLabel",
                     font=("Segoe UI", 9, "bold"), width=8).pack(side=tk.LEFT)
            self.meta_labels[key] = ttk.Label(row, text="", style="Card.TLabel",
                                             font=("Segoe UI", 9), wraplength=250)
            self.meta_labels[key].pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # ── Analysis section ──
        self.analysis_card = CardFrame(self.scroll_frame, self.theme, "🤖 AI Analysis")
        self.analysis_card.pack(fill=tk.X, padx=8, pady=4)
        self.analysis_content = self.analysis_card.content
        
        self.analysis_labels = {}
        analysis_fields = [
            ("summary", "Summary:"),
            ("category", "Category:"),
            ("subcategory", "Subcategory:"),
            ("project", "Project:"),
            ("action", "Action:"),
            ("confidence", "Confidence:"),
            ("importance", "Importance:"),
            ("lifecycle", "Lifecycle:"),
            ("sentimental", "Sentimental:"),
        ]
        for key, label in analysis_fields:
            row = ttk.Frame(self.analysis_content, style="Card.TFrame")
            row.pack(fill=tk.X, pady=1)
            ttk.Label(row, text=label, style="Card.TLabel",
                     font=("Segoe UI", 9, "bold"), width=12).pack(side=tk.LEFT)
            lbl = ttk.Label(row, text="", style="Card.TLabel",
                           font=("Segoe UI", 9), wraplength=220)
            lbl.pack(side=tk.LEFT, fill=tk.X, expand=True)
            self.analysis_labels[key] = lbl
        
        # ── Tags section ──
        self.tags_card = CardFrame(self.scroll_frame, self.theme, "🏷 Tags")
        self.tags_card.pack(fill=tk.X, padx=8, pady=4)
        self.tags_content = self.tags_card.content
        
        # ── Reasoning section ──
        self.reason_card = CardFrame(self.scroll_frame, self.theme, "💡 Reasoning")
        self.reason_card.pack(fill=tk.X, padx=8, pady=4)
        self.reason_label = ttk.Label(self.reason_card.content, text="",
                                     style="Card.TLabel", wraplength=300,
                                     font=("Segoe UI", 9))
        self.reason_label.pack(fill=tk.X, padx=4, pady=4)
        
        # ── Preview section ──
        self.preview_card = CardFrame(self.scroll_frame, self.theme, "📝 Preview")
        self.preview_card.pack(fill=tk.X, padx=8, pady=4)
        
        self.preview_text = tk.Text(self.preview_card.content,
                                   height=8, width=40,
                                   font=("Consolas", 9),
                                   bg=self.theme.colors["input_bg"],
                                   fg=self.theme.colors["fg"],
                                   wrap=tk.WORD,
                                   relief="solid",
                                   borderwidth=1)
        self.preview_text.pack(fill=tk.X, padx=4, pady=4)
        
        # ── Empty state ──
        self.empty_frame = ttk.Frame(self.scroll_frame, style="Panel.TFrame")
        self.empty_frame.pack(fill=tk.BOTH, expand=True, pady=40)
        
        ttk.Label(self.empty_frame, text="👆",
                 font=("Segoe UI", 32)).pack()
        ttk.Label(self.empty_frame, text="Select a file to view details",
                 style="Muted.TLabel",
                 font=("Segoe UI", 11)).pack(pady=(8, 0))
        ttk.Label(self.empty_frame, text="Double-click or press Enter",
                 style="Muted.TLabel",
                 font=("Segoe UI", 9)).pack()

    def _show_empty(self):
        """Show empty state."""
        self.empty_frame.pack(fill=tk.BOTH, expand=True, pady=40)
        self.meta_card.pack_forget()
        self.analysis_card.pack_forget()
        self.tags_card.pack_forget()
        self.reason_card.pack_forget()
        self.preview_card.pack_forget()

    def _show_content(self):
        """Show content sections."""
        self.empty_frame.pack_forget()
        self.meta_card.pack(fill=tk.X, padx=8, pady=4)
        self.analysis_card.pack(fill=tk.X, padx=8, pady=4)
        self.tags_card.pack(fill=tk.X, padx=8, pady=4)
        self.reason_card.pack(fill=tk.X, padx=8, pady=4)
        self.preview_card.pack(fill=tk.X, padx=8, pady=4)

    def show_file(self, entry):
        """Display a file's details in the panel."""
        self._current_entry = entry
        
        if not entry:
            self._show_empty()
            return
        
        self._show_content()
        
        # Get values from dict or object
        if isinstance(entry, dict):
            get_val = lambda k: entry.get(k, "")
        else:
            get_val = lambda k: getattr(entry, k, "")
        
        filename = get_val("file") or Path(get_val("path") or "").name or "Unknown"
        self.file_name_label["text"] = filename
        
        # Metadata
        path = get_val("path")
        self.meta_labels["path"]["text"] = path
        self.meta_labels["size"]["text"] = get_val("size_human") or self._get_file_size(path)
        self.meta_labels["extension"]["text"] = get_val("extension")
        self.meta_labels["modified"]["text"] = get_val("modified")
        
        # Analysis
        self.analysis_labels["summary"]["text"] = get_val("summary") or "No summary"
        
        category = get_val("category") or "Other"
        cat_icon = get_category_icon(category)
        self.analysis_labels["category"]["text"] = f"{cat_icon} {category}"
        
        self.analysis_labels["subcategory"]["text"] = get_val("subcategory") or ""
        
        project = get_val("project")
        self.analysis_labels["project"]["text"] = project if project else "Not detected"
        
        action = get_val("action") or "Review"
        action_icon = get_action_icon(action)
        action_color = self.theme.get_action_color(action)
        self.analysis_labels["action"]["text"] = f"{action_icon} {action}"
        self.analysis_labels["action"]["foreground"] = action_color
        
        confidence = get_val("confidence")
        conf_icon = get_confidence_icon(int(confidence) if confidence else 0)
        conf_color = self.theme.get_confidence_color(int(confidence) if confidence else 0)
        self.analysis_labels["confidence"]["text"] = f"{conf_icon} {confidence}%"
        self.analysis_labels["confidence"]["foreground"] = conf_color
        
        self.analysis_labels["importance"]["text"] = f"{get_val('importance')}/10"
        
        lifecycle = get_val("lifecycle") or "Unknown"
        lc_icon = get_lifecycle_icon(lifecycle)
        self.analysis_labels["lifecycle"]["text"] = f"{lc_icon} {lifecycle}"
        
        sentimental = get_val("sentimental_value") or 1
        self.analysis_labels["sentimental"]["text"] = f"{sentimental}/10"
        
        # Tags
        for child in self.tags_content.winfo_children():
            child.destroy()
        
        tags = get_val("tags") or []
        if tags:
            tag_frame = ttk.Frame(self.tags_content, style="Card.TFrame")
            tag_frame.pack(fill=tk.X, pady=4)
            for tag in tags:
                display = tag.split(":", 1)[1].replace("-", " ").title() if ":" in tag else tag
                lbl = ttk.Label(tag_frame, text=f" {display} ",
                              style="Card.TLabel",
                              font=("Segoe UI", 8))
                lbl.pack(side=tk.LEFT, padx=2, pady=1)
        else:
            ttk.Label(self.tags_content, text="No tags",
                     style="Muted.TLabel").pack(pady=4)
        
        # Reasoning
        reasoning = get_val("reasoning") or "No reasoning provided."
        self.reason_label["text"] = reasoning
        
        # Preview
        self.preview_text.delete("1.0", tk.END)
        try:
            if path and Path(path).is_file():
                with open(path, "r", encoding="utf-8", errors="replace") as f:
                    preview = f.read(2000)
                self.preview_text.insert("1.0", preview)
            else:
                self.preview_text.insert("1.0", "[File not accessible for preview]")
        except Exception:
            self.preview_text.insert("1.0", "[Preview not available]")
        
        self.preview_text.config(state=tk.DISABLED)

    def _get_file_size(self, path: str) -> str:
        """Get human-readable file size."""
        try:
            size = Path(path).stat().st_size
            for unit in ["B", "KB", "MB", "GB"]:
                if size < 1024:
                    return f"{size:.2f} {unit}"
                size /= 1024
            return f"{size:.2f} TB"
        except OSError:
            return "Unknown"

    def clear(self):
        """Clear the detail panel."""
        self._current_entry = None
        self._show_empty()