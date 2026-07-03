"""
Keyboard shortcut manager for AI File Manager GUI.

Centralizes all keyboard bindings and provides shortcut discovery
(displaying available shortcuts in menus and tooltips).
"""

import tkinter as tk
from typing import Callable, Optional


class ShortcutManager:
    """
    Manages keyboard shortcuts for the application.
    
    Binds keys to callbacks and provides a registry for shortcut display.
    """

    def __init__(self, root: tk.Tk):
        self.root = root
        self._bindings: dict = {}  # key_sequence -> (description, callback)

    def bind(self, key_sequence: str, callback: Callable, description: str = ""):
        """
        Register a keyboard shortcut.
        
        Args:
            key_sequence: e.g., "<Control-o>", "<F5>", "<Delete>"
            callback: Function to call (no arguments)
            description: Human-readable description for menus/tooltips
        """
        self._bindings[key_sequence] = (description, callback)
        self.root.bind_all(key_sequence, lambda e, cb=callback: cb())

    def get_all_shortcuts(self) -> list:
        """Return list of (key_sequence, description) tuples for display."""
        result = []
        for key_seq, (desc, _) in self._bindings.items():
            if desc:
                # Convert internal format to display format
                display = self._to_display(key_seq)
                result.append((display, desc))
        return sorted(result, key=lambda x: x[0])

    def _to_display(self, key_sequence: str) -> str:
        """Convert internal key sequence to display string."""
        display = key_sequence.strip("<>")
        parts = display.split("-")
        # Capitalize first letter of each part
        return "+".join(p.capitalize() if len(p) > 1 else p.upper() for p in parts)

    def setup_defaults(self, app):
        """
        Set up default keyboard shortcuts for the application.
        
        Args:
            app: The AIFileManagerApp instance with action methods
        """
        self.bind("<Control-o>", app.pick_folder, "Scan a folder")
        self.bind("<Control-n>", app.pick_file, "Analyze a single file")
        self.bind("<Control-l>", app.load_reports, "Load saved reports")
        self.bind("<Control-f>", app.focus_query, "Focus query bar")
        self.bind("<Control-d>", app.toggle_dark_mode, "Toggle dark mode")
        self.bind("<Control-e>", app.export_csv, "Export results as CSV")
        self.bind("<Control-a>", app.select_all, "Select all results")
        self.bind("<Control-q>", app.quit, "Quit application")
        self.bind("<F5>", app.refresh_scan, "Re-scan current directory")
        self.bind("<Delete>", app.mark_for_deletion, "Mark selected for deletion")
        self.bind("<Return>", app.show_detail, "Show file details")
        self.bind("<space>", app.preview_file, "Preview selected file")
        self.bind("<Control-Shift-C>", app.clear_results, "Clear all results")
        self.bind("<Escape>", app.clear_selection, "Clear selection")