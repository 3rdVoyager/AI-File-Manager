"""
Query panel for AI File Manager GUI.

Provides natural-language querying of analysis results, query history,
and quick preset query buttons.
"""

import tkinter as tk
from tkinter import ttk
from typing import Optional, Callable

from gui.theme import ThemeManager
from gui.icons import SEARCH, HISTORY, CLEANUP, SUGGESTIONS


class QueryPanel(ttk.Frame):
    """
    Query bar with preset buttons and history.
    
    Layout:
    ┌──────────────────────────────────────────────────────┐
    │  🔍 [__________________________] [Ask AI]  [Clear]  │
    │  [💡 Show me files safe to delete] [📁 Group by...] │
    └──────────────────────────────────────────────────────┘
    """

    def __init__(self, parent, theme: ThemeManager,
                 on_query: Optional[Callable[[str], None]] = None):
        super().__init__(parent, style="Panel.TFrame")
        self.theme = theme
        self._on_query = on_query
        self._history = []
        self._history_index = -1
        
        self._build_ui()

    def _build_ui(self):
        """Construct the query panel layout."""
        # ── Query input row ──
        input_frame = ttk.Frame(self, style="Panel.TFrame")
        input_frame.pack(fill=tk.X, padx=8, pady=(6, 2))
        
        # Search icon
        ttk.Label(input_frame, text=SEARCH, style="Secondary.TLabel",
                 font=("Segoe UI", 12)).pack(side=tk.LEFT, padx=(0, 4))
        
        # Query entry
        self.query_var = tk.StringVar()
        self.query_entry = ttk.Entry(input_frame, textvariable=self.query_var,
                                    font=("Segoe UI", 10))
        self.query_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4))
        self.query_entry.bind("<Return>", lambda e: self._submit_query())
        self.query_entry.bind("<Up>", self._history_back)
        self.query_entry.bind("<Down>", self._history_forward)
        self.query_entry.bind("<Escape>", lambda e: self.query_var.set(""))
        
        # Ask button
        ttk.Button(input_frame, text="Ask AI", style="Accent.TButton",
                  command=self._submit_query).pack(side=tk.LEFT, padx=2)
        
        # Clear button
        ttk.Button(input_frame, text="✕", style="Toolbar.TButton",
                  command=lambda: self.query_var.set("")).pack(side=tk.LEFT)
        
        # ── Preset queries row ──
        presets_frame = ttk.Frame(self, style="Panel.TFrame")
        presets_frame.pack(fill=tk.X, padx=8, pady=(2, 6))
        
        presets = [
            (f"{CLEANUP} Safe to delete", "Show me files that are probably safe to delete"),
            ("📂 Group by project", "Group the files by project"),
            ("📦 Find installers", "List all installer or setup files"),
            ("⚠ Needs review", "Show me files that need manual review"),
            ("📊 Summary", "Give me a summary of all files"),
        ]
        
        for label, query in presets:
            btn = ttk.Button(presets_frame, text=label, style="Toolbar.TButton",
                           command=lambda q=query: self._set_query(q))
            btn.pack(side=tk.LEFT, padx=2)
        
        # Status label (hidden by default)
        self.status_label = ttk.Label(self, text="", style="Muted.TLabel",
                                     font=("Segoe UI", 9))
        self.status_label.pack(padx=8, pady=(0, 4))

    def _submit_query(self):
        """Submit the current query."""
        question = self.query_var.get().strip()
        if not question:
            return
        
        # Add to history
        self._history.append(question)
        self._history_index = len(self._history)
        
        # Show status
        self.status_label["text"] = "🤔 Thinking..."
        self.update_idletasks()
        
        if self._on_query:
            self._on_query(question)

    def _set_query(self, question: str):
        """Set the query text and submit."""
        self.query_var.set(question)
        self._submit_query()

    def _history_back(self, event):
        """Navigate backward through query history."""
        if not self._history:
            return
        self._history_index = max(0, self._history_index - 1)
        self.query_var.set(self._history[self._history_index])

    def _history_forward(self, event):
        """Navigate forward through query history."""
        if not self._history:
            return
        self._history_index = min(len(self._history), self._history_index + 1)
        if self._history_index >= len(self._history):
            self.query_var.set("")
        else:
            self.query_var.set(self._history[self._history_index])

    def show_result(self, text: str):
        """Display a query result in the status area."""
        self.status_label["text"] = text[:200]

    def show_error(self, error: str):
        """Display an error message."""
        self.status_label["text"] = f"⚠ {error[:200]}"
        self.status_label.configure(style="Danger.TLabel")

    def focus(self):
        """Focus the query entry."""
        self.query_entry.focus_set()
        self.query_entry.selection_range(0, tk.END)

    def clear(self):
        """Clear the query input and status."""
        self.query_var.set("")
        self.status_label["text"] = ""