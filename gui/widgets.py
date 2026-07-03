"""
Reusable GUI widgets for AI File Manager.

Custom tkinter widgets used throughout the application:
- ProgressOverlay: Animated scanning progress with file count + time
- CardFrame: Bordered container for dashboard cards
- TagLabel: Colored tag display
- ActionBadge: Color-coded action indicator
- IconButton: Button with icon and optional text
"""

import tkinter as tk
from tkinter import ttk
import time
from typing import Optional

from gui.theme import ThemeManager
from gui.icons import get_action_icon


class CardFrame(ttk.Frame):
    """A bordered card-style container for dashboard sections."""

    def __init__(self, parent, theme: ThemeManager, title: str = "", **kwargs):
        super().__init__(parent, style="Card.TFrame", **kwargs)
        self.theme = theme
        
        # Card border effect via separator
        if title:
            header = ttk.Frame(self, style="Card.TFrame")
            header.pack(fill=tk.X, padx=12, pady=(8, 0))
            
            ttk.Label(header, text=title, style="Heading.TLabel",
                     font=("Segoe UI", 11, "bold")).pack(side=tk.LEFT)
            
            ttk.Separator(self, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=8, pady=8)
        
        # Content frame (for subclasses to fill)
        self.content = ttk.Frame(self, style="Card.TFrame")
        self.content.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 12))


class ProgressOverlay(tk.Frame):
    """
    Animated progress overlay for scanning operations.
    
    Shows:
    - Current file being analyzed
    - Progress bar
    - File count (x of y)
    - Elapsed time
    - Cached vs new breakdown
    """

    def __init__(self, parent, theme: ThemeManager):
        super().__init__(parent, bg=theme.colors["card_bg"],
                        highlightbackground=theme.colors["card_border"],
                        highlightthickness=1)
        self.theme = theme
        self._start_time = 0.0
        self._running = False
        
        # Close button
        close_btn = tk.Button(self, text="✕", bg=theme.colors["card_bg"],
                             fg=theme.colors["fg"], bd=0,
                             font=("Segoe UI", 10),
                             command=self.hide)
        close_btn.place(relx=1.0, x=-8, y=8, anchor="ne")
        
        # Status label
        self.status_label = ttk.Label(self, text="Scanning...",
                                     style="Heading.TLabel",
                                     font=("Segoe UI", 12, "bold"))
        self.status_label.pack(pady=(16, 4))
        
        # Current file label
        self.file_label = ttk.Label(self, text="",
                                   style="Secondary.TLabel",
                                   font=("Segoe UI", 9))
        self.file_label.pack(pady=(0, 8))
        
        # Progress bar
        self.progress = ttk.Progressbar(self, length=300, mode="determinate")
        self.progress.pack(pady=(0, 8))
        
        # File count
        self.count_label = ttk.Label(self, text="", style="Muted.TLabel")
        self.count_label.pack(pady=(0, 4))
        
        # Stats row (cached, new, errors)
        stats_frame = ttk.Frame(self)
        stats_frame.pack(pady=(0, 12))
        
        self.cached_label = ttk.Label(stats_frame, text="⚡ 0 cached",
                                     style="Muted.TLabel")
        self.cached_label.pack(side=tk.LEFT, padx=8)
        
        self.new_label = ttk.Label(stats_frame, text="🆕 0 new",
                                  style="Muted.TLabel")
        self.new_label.pack(side=tk.LEFT, padx=8)
        
        self.errors_label = ttk.Label(stats_frame, text="✕ 0 errors",
                                     style="Muted.TLabel")
        self.errors_label.pack(side=tk.LEFT, padx=8)
        
        # Elapsed time (updated every second)
        self.time_label = ttk.Label(self, text="", style="Muted.TLabel",
                                   font=("Segoe UI", 8))
        self.time_label.pack(pady=(0, 12))
        
        # Start hidden
        self.pack_forget()

    def show(self):
        """Show the overlay and reset state."""
        self._start_time = time.time()
        self._running = True
        self.update()
        self.pack(fill=tk.X, padx=10, pady=5)
        self._update_time()

    def hide(self):
        """Hide the overlay."""
        self._running = False
        self.pack_forget()

    def update_progress(self, current: int, total: int, filename: str = "",
                       cached: int = 0, new_count: int = 0, errors: int = 0):
        """Update progress display."""
        if total > 0:
            pct = int(current / total * 100)
            self.progress["value"] = pct
            self.count_label["text"] = f"{current} of {total} files ({pct}%)"
        
        if filename:
            # Truncate long filenames
            name = filename if len(filename) <= 50 else "..." + filename[-47:]
            self.file_label["text"] = f"📄 {name}"
        
        self.cached_label["text"] = f"⚡ {cached} cached"
        self.new_label["text"] = f"🆕 {new_count} new"
        self.errors_label["text"] = f"✕ {errors} errors"
        
        self.update_idletasks()

    def _update_time(self):
        """Update elapsed time display every second."""
        if not self._running:
            return
        
        elapsed = time.time() - self._start_time
        if elapsed < 60:
            time_str = f"{elapsed:.0f}s"
        else:
            time_str = f"{elapsed // 60:.0f}m {elapsed % 60:.0f}s"
        
        self.time_label["text"] = f"⏱ {time_str}"
        self.after(1000, self._update_time)

    def set_done(self, message: str = "Complete!"):
        """Show completion state."""
        self._running = False
        self.status_label["text"] = f"✓ {message}"
        self.status_label.configure(style="Success.TLabel")
        self.file_label["text"] = ""
        self.progress["value"] = 100


class ActionBadge(ttk.Label):
    """Color-coded action badge showing Keep/Delete/Archive/Review."""

    def __init__(self, parent, theme: ThemeManager, action: str, **kwargs):
        self._theme = theme
        super().__init__(parent, **kwargs)
        self.set_action(action)

    def set_action(self, action: str):
        """Update the badge to show a different action."""
        icon = get_action_icon(action)
        color = self._theme.get_action_color(action)
        self.configure(text=f" {icon} {action} ",
                      foreground=color,
                      font=("Segoe UI", 9, "bold"))


class TagLabel(ttk.Label):
    """A small tag label for displaying file tags."""

    def __init__(self, parent, tag: str, **kwargs):
        display = tag.split(":", 1)[1].replace("-", " ").title() if ":" in tag else tag
        super().__init__(parent, text=f" {display} ",
                        font=("Segoe UI", 8),
                        **kwargs)


class StatusBar(ttk.Frame):
    """
    Application status bar showing:
    - Status message (left)
    - File count (right)
    - Optional loading indicator
    """

    def __init__(self, parent, theme: ThemeManager):
        super().__init__(parent, style="Panel.TFrame")
        self.theme = theme
        
        # Status message (left)
        self.status_label = ttk.Label(self, text="Ready.",
                                     style="Secondary.TLabel",
                                     font=("Segoe UI", 9))
        self.status_label.pack(side=tk.LEFT, padx=8, pady=2)
        
        # File count (right)
        self.count_label = ttk.Label(self, text="",
                                    style="Muted.TLabel",
                                    font=("Segoe UI", 9))
        self.count_label.pack(side=tk.RIGHT, padx=8, pady=2)
        
        # Configure the frame
        self.configure(height=24)

    def set_status(self, message: str):
        """Update the status message."""
        self.status_label["text"] = str(message)
        self.update_idletasks()

    def set_count(self, count: int, total: int = 0):
        """Update the file count display."""
        if total:
            self.count_label["text"] = f"{count} of {total} files"
        else:
            self.count_label["text"] = f"{count} files"
        self.update_idletasks()

    def clear_count(self):
        """Clear the file count display."""
        self.count_label["text"] = ""


class ToolbarButton(ttk.Button):
    """A toolbar button with icon and text, using flat style."""

    def __init__(self, parent, text: str = "", icon: str = "",
                 command=None, tooltip: str = "", **kwargs):
        display = f" {icon} {text}" if icon else text
        super().__init__(parent, text=display, command=command,
                        style="Toolbar.TButton", **kwargs)
        
        if tooltip:
            self._create_tooltip(tooltip)

    def _create_tooltip(self, text: str):
        """Create a simple tooltip that appears on hover."""
        tooltip = None
        
        def show_tip(event):
            nonlocal tooltip
            if tooltip:
                return
            x = event.widget.winfo_rootx() + 20
            y = event.widget.winfo_rooty() + 20
            tooltip = tk.Toplevel(event.widget)
            tooltip.wm_overrideredirect(True)
            tooltip.wm_geometry(f"+{x}+{y}")
            label = ttk.Label(tooltip, text=text, background="#FFFFDD",
                            foreground="#333333", relief="solid",
                            borderwidth=1, padding=(4, 2),
                            font=("Segoe UI", 8))
            label.pack()
        
        def hide_tip(event):
            nonlocal tooltip
            if tooltip:
                tooltip.destroy()
                tooltip = None
        
        self.bind("<Enter>", show_tip)
        self.bind("<Leave>", hide_tip)