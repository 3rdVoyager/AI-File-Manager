"""
Theme engine for AI File Manager GUI.

Provides dark and light color palettes, ttk style configurations,
and utility functions for consistent theming across the application.
"""

import tkinter as tk
from tkinter import ttk


# ─── Color palettes ──────────────────────────────────────────────────────────

LIGHT_THEME = {
    "bg": "#F5F5F5",
    "fg": "#1A1A1A",
    "select_bg": "#0078D4",
    "select_fg": "#FFFFFF",
    "accent": "#0078D4",
    "accent_hover": "#106EBE",
    "card_bg": "#FFFFFF",
    "card_border": "#E0E0E0",
    "panel_bg": "#FAFAFA",
    "input_bg": "#FFFFFF",
    "input_border": "#CCCCCC",
    "status_bg": "#E8E8E8",
    "danger": "#D32F2F",
    "warning": "#F57C00",
    "success": "#388E3C",
    "info": "#1976D2",
    "text_secondary": "#666666",
    "text_muted": "#999999",
    "separator": "#E0E0E0",
    "highlight": "#E3F2FD",
    # Action colors
    "action_keep": "#388E3C",
    "action_delete": "#D32F2F",
    "action_archive": "#1976D2",
    "action_review": "#F57C00",
}

DARK_THEME = {
    "bg": "#1E1E1E",
    "fg": "#D4D4D4",
    "select_bg": "#264F78",
    "select_fg": "#FFFFFF",
    "accent": "#007ACC",
    "accent_hover": "#1A85D9",
    "card_bg": "#252526",
    "card_border": "#3C3C3C",
    "panel_bg": "#1E1E1E",
    "input_bg": "#3C3C3C",
    "input_border": "#555555",
    "status_bg": "#007ACC",
    "danger": "#F44747",
    "warning": "#CCA700",
    "success": "#4EC9B0",
    "info": "#3794FF",
    "text_secondary": "#969696",
    "text_muted": "#6E6E6E",
    "separator": "#3C3C3C",
    "highlight": "#2A2D2E",
    # Action colors
    "action_keep": "#4EC9B0",
    "action_delete": "#F44747",
    "action_archive": "#3794FF",
    "action_review": "#CCA700",
}

# Font families
FONT_FAMILY = "Segoe UI"
FONT_MONO = "Consolas"
FONT_SIZE = 10
FONT_SIZE_SMALL = 9
FONT_SIZE_LARGE = 12
FONT_SIZE_TITLE = 16


class ThemeManager:
    """Manages theme state and provides styling utilities."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self._dark_mode = False
        self.colors = dict(LIGHT_THEME)
        self._setup_styles()

    @property
    def is_dark(self) -> bool:
        return self._dark_mode

    def toggle(self):
        """Toggle between dark and light mode."""
        self._dark_mode = not self._dark_mode
        self.colors = dict(DARK_THEME if self._dark_mode else LIGHT_THEME)
        self._apply_theme()

    def set_dark(self, dark: bool):
        """Explicitly set dark mode."""
        if dark != self._dark_mode:
            self.toggle()

    def _setup_styles(self):
        """Initialize ttk styles (called once at startup)."""
        self.style = ttk.Style(self.root)
        # Use 'clam' theme as base — it's the most customizable
        available = self.style.theme_names()
        if "clam" in available:
            self.style.theme_use("clam")
        
        self._apply_theme()

    def _apply_theme(self):
        """Apply current theme colors to all ttk widgets."""
        c = self.colors
        
        # Root window
        self.root.configure(bg=c["bg"])
        
        # ttk styles
        self.style.configure(".", background=c["bg"], foreground=c["fg"],
                             font=(FONT_FAMILY, FONT_SIZE))
        
        # TFrame
        self.style.configure("TFrame", background=c["bg"])
        self.style.configure("Card.TFrame", background=c["card_bg"])
        self.style.configure("Panel.TFrame", background=c["panel_bg"])
        
        # TLabel
        self.style.configure("TLabel", background=c["bg"], foreground=c["fg"])
        self.style.configure("Card.TLabel", background=c["card_bg"], foreground=c["fg"])
        self.style.configure("Heading.TLabel", font=(FONT_FAMILY, FONT_SIZE_LARGE, "bold"))
        self.style.configure("Title.TLabel", font=(FONT_FAMILY, FONT_SIZE_TITLE, "bold"))
        self.style.configure("Secondary.TLabel", foreground=c["text_secondary"])
        self.style.configure("Muted.TLabel", foreground=c["text_muted"])
        self.style.configure("Success.TLabel", foreground=c["success"])
        self.style.configure("Danger.TLabel", foreground=c["danger"])
        self.style.configure("Warning.TLabel", foreground=c["warning"])
        
        # TButton
        self.style.configure("TButton", background=c["card_bg"], foreground=c["fg"],
                            borderwidth=1, focusthickness=0, padding=(8, 4))
        self.style.map("TButton",
                       background=[("active", c["accent_hover"]),
                                  ("pressed", c["accent"])],
                       foreground=[("active", "#FFFFFF")])
        
        # Accent Button
        self.style.configure("Accent.TButton", background=c["accent"], foreground="#FFFFFF",
                            borderwidth=0, padding=(12, 6))
        self.style.map("Accent.TButton",
                       background=[("active", c["accent_hover"]),
                                  ("pressed", c["accent"])])
        
        # Toolbar Button (flat, more compact)
        self.style.configure("Toolbar.TButton", background=c["bg"], foreground=c["fg"],
                            borderwidth=0, padding=(6, 2))
        self.style.map("Toolbar.TButton",
                       background=[("active", c["highlight"])],
                       relief=[("active", "flat")])
        
        # TEntry
        self.style.configure("TEntry", fieldbackground=c["input_bg"],
                            foreground=c["fg"], borderwidth=1,
                            insertcolor=c["fg"])  # cursor color
        
        # TCombobox
        self.style.configure("TCombobox", fieldbackground=c["input_bg"],
                            foreground=c["fg"], selectbackground=c["select_bg"],
                            selectforeground=c["select_fg"])
        
        # TLabelframe
        self.style.configure("TLabelframe", background=c["bg"], foreground=c["fg"])
        self.style.configure("TLabelframe.Label", background=c["bg"], foreground=c["fg"])
        
        # Treeview
        self.style.configure("Treeview", background=c["card_bg"], foreground=c["fg"],
                            fieldbackground=c["card_bg"], borderwidth=0,
                            rowheight=28)
        self.style.map("Treeview",
                       background=[("selected", c["select_bg"])],
                       foreground=[("selected", c["select_fg"])])
        self.style.configure("Treeview.Heading", background=c["panel_bg"],
                            foreground=c["fg"], borderwidth=1,
                            relief="solid", padding=(4, 2))
        self.style.map("Treeview.Heading",
                       background=[("active", c["highlight"])])
        
        # TScrollbar
        self.style.configure("TScrollbar", background=c["panel_bg"],
                            troughcolor=c["bg"], bordercolor=c["separator"],
                            arrowcolor=c["fg"])
        
        # TProgressbar
        self.style.configure("TProgressbar", background=c["accent"],
                            troughcolor=c["separator"], borderwidth=0)
        
        # TSeparator
        self.style.configure("TSeparator", background=c["separator"])
        
        # Sizegrip
        self.style.configure("TSizegrip", background=c["bg"])

    def get_action_color(self, action: str) -> str:
        """Return the display color for a file action."""
        return {
            "Keep": self.colors["action_keep"],
            "Delete": self.colors["action_delete"],
            "Archive": self.colors["action_archive"],
            "Review": self.colors["action_review"],
        }.get(action, self.colors["fg"])

    def get_confidence_color(self, confidence: int) -> str:
        """Return color based on confidence level."""
        if confidence >= 85:
            return self.colors["success"]
        elif confidence >= 60:
            return self.colors["warning"]
        return self.colors["danger"]