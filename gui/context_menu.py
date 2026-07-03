"""
Context menu factory for AI File Manager GUI.

Provides right-click menu functionality for file results,
with actions like "Explain recommendation", "Find similar",
"Show in Explorer", "Copy path", and "Mark for review".
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, Callable
from pathlib import Path
import subprocess
import json

from gui.theme import ThemeManager


class ContextMenu:
    """
    Manages right-click context menus for the results table.
    """

    def __init__(self, parent, theme: ThemeManager):
        self.parent = parent
        self.theme = theme
        
        # Create the menu
        self.menu = tk.Menu(parent, tearoff=0,
                           bg=theme.colors["card_bg"],
                           fg=theme.colors["fg"],
                           activebackground=theme.colors["select_bg"],
                           activeforeground=theme.colors["select_fg"],
                           font=("Segoe UI", 9))
        
        # Callbacks (set by app)
        self.on_explain: Optional[Callable] = None
        self.on_find_similar: Optional[Callable] = None
        self.on_show_in_explorer: Optional[Callable] = None
        self.on_copy_path: Optional[Callable] = None
        self.on_mark_review: Optional[Callable] = None
        self.on_export_entry: Optional[Callable] = None

    def build_menu(self, entry):
        """Build and return the context menu for a given entry."""
        self.menu.delete(0, tk.END)
        
        if not entry:
            return self.menu
        
        # File info header (disabled)
        filename = entry.get("file", "Unknown") if isinstance(entry, dict) else getattr(entry, "file", "Unknown")
        self.menu.add_command(label=f"  {filename}", state=tk.DISABLED,
                            font=("Segoe UI", 9, "italic"))
        self.menu.add_separator()
        
        # Actions
        self.menu.add_command(label="🤖 Explain recommendation",
                            command=lambda: self._safe_call(self.on_explain, entry))
        self.menu.add_command(label="🔍 Find similar files",
                            command=lambda: self._safe_call(self.on_find_similar, entry))
        self.menu.add_separator()
        self.menu.add_command(label="📂 Show in Explorer",
                            command=lambda: self._safe_call(self.on_show_in_explorer, entry))
        self.menu.add_command(label="📋 Copy path",
                            command=lambda: self._safe_call(self.on_copy_path, entry))
        self.menu.add_separator()
        self.menu.add_command(label="⚠ Toggle review flag",
                            command=lambda: self._safe_call(self.on_mark_review, entry))
        self.menu.add_command(label="💾 Export entry as JSON",
                            command=lambda: self._safe_call(self.on_export_entry, entry))
        
        return self.menu

    def show(self, event, entry):
        """Show the context menu at the event position."""
        if not entry:
            return
        self.build_menu(entry)
        self.menu.tk_popup(event.x_root, event.y_root)

    def _safe_call(self, callback, *args):
        """Safely call a callback if it exists."""
        if callback:
            try:
                callback(*args)
            except Exception as e:
                messagebox.showerror("Error", str(e))


def show_in_explorer(file_path: str):
    """Open the file's containing folder in the system file manager."""
    try:
        path = Path(file_path)
        if path.is_file():
            # Windows: select the file
            subprocess.Popen(["explorer", "/select,", str(path)])
    except Exception:
        pass


def copy_to_clipboard(root: tk.Tk, text: str):
    """Copy text to system clipboard."""
    root.clipboard_clear()
    root.clipboard_append(text)
    root.update()