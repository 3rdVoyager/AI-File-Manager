"""
Results table panel for AI File Manager GUI.

Displays analysis results in a sortable, filterable Treeview table
with color-coded action badges, multi-select, and column customization.
"""

import tkinter as tk
from tkinter import ttk
from typing import Optional, Callable

from gui.theme import ThemeManager
from gui.icons import get_action_icon, get_category_icon, get_confidence_icon
from scripts.query_engine import keyword_filter


# ─── Column definitions ──────────────────────────────────────────────────────

COLUMNS = (
    "file", "category", "subcategory", "project",
    "action", "importance", "lifecycle", "confidence", "tags"
)

COLUMN_HEADINGS = {
    "file": "File",
    "category": "Category",
    "subcategory": "Subcategory",
    "project": "Project",
    "action": "Action",
    "importance": "Imp.",
    "lifecycle": "Lifecycle",
    "confidence": "Conf.",
    "tags": "Tags",
}

COLUMN_WIDTHS = {
    "file": 280,
    "category": 110,
    "subcategory": 100,
    "project": 130,
    "action": 80,
    "importance": 55,
    "lifecycle": 85,
    "confidence": 65,
    "tags": 150,
}

# Columns that are sortable
SORTABLE_COLUMNS = set(COLUMNS)


class ResultsPanel(ttk.Frame):
    """
    Sortable, filterable results table with multi-select.
    
    Features:
    - Click column headers to sort
    - Color-coded action badges
    - Multi-select with Ctrl/Shift
    - Right-click context menu
    - Filter bar with dropdowns
    - Search-as-you-type
    """

    def __init__(self, parent, theme: ThemeManager,
                 on_selection_change: Optional[Callable] = None,
                 on_double_click: Optional[Callable] = None):
        super().__init__(parent, style="Panel.TFrame")
        self.theme = theme
        self._on_selection_change = on_selection_change
        self._on_double_click = on_double_click
        
        self._results = []  # Full unfiltered results
        self._filtered = []  # Currently displayed results
        self._sort_column = "file"
        self._sort_reverse = False
        
        self._build_ui()

    def _build_ui(self):
        """Construct the results panel layout."""
        # ── Filter bar ──
        filter_frame = ttk.Frame(self, style="Panel.TFrame")
        filter_frame.pack(fill=tk.X, padx=8, pady=(8, 4))
        
        # Search entry
        ttk.Label(filter_frame, text="🔍", style="Secondary.TLabel").pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_var.trace("w", lambda *a: self._apply_filters())
        search_entry = ttk.Entry(filter_frame, textvariable=self.search_var, width=20)
        search_entry.pack(side=tk.LEFT, padx=(4, 8))
        search_entry.bind("<Escape>", lambda e: self.search_var.set(""))
        
        # Category filter
        ttk.Label(filter_frame, text="Category:", style="Secondary.TLabel",
                 font=("Segoe UI", 9)).pack(side=tk.LEFT)
        self.category_var = tk.StringVar(value="All")
        self.category_combo = ttk.Combobox(filter_frame, textvariable=self.category_var,
                                          state="readonly", width=14)
        self.category_combo["values"] = ["All"]
        self.category_combo.pack(side=tk.LEFT, padx=4)
        self.category_combo.bind("<<ComboboxSelected>>", lambda e: self._apply_filters())
        
        # Action filter
        ttk.Label(filter_frame, text="Action:", style="Secondary.TLabel",
                 font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=(8, 0))
        self.action_var = tk.StringVar(value="All")
        self.action_combo = ttk.Combobox(filter_frame, textvariable=self.action_var,
                                        state="readonly", width=10)
        self.action_combo["values"] = ["All", "Keep", "Delete", "Archive", "Review"]
        self.action_combo.pack(side=tk.LEFT, padx=4)
        self.action_combo.bind("<<ComboboxSelected>>", lambda e: self._apply_filters())
        
        # Lifecycle filter
        ttk.Label(filter_frame, text="Lifecycle:", style="Secondary.TLabel",
                 font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=(8, 0))
        self.lifecycle_var = tk.StringVar(value="All")
        self.lifecycle_combo = ttk.Combobox(filter_frame, textvariable=self.lifecycle_var,
                                           state="readonly", width=10)
        self.lifecycle_combo["values"] = ["All", "Active", "Dormant", "Archived", "Transient"]
        self.lifecycle_combo.pack(side=tk.LEFT, padx=4)
        self.lifecycle_combo.bind("<<ComboboxSelected>>", lambda e: self._apply_filters())
        
        # Clear filters button
        clear_btn = ttk.Button(filter_frame, text="✕ Clear", command=self._clear_filters,
                              style="Toolbar.TButton")
        clear_btn.pack(side=tk.RIGHT, padx=4)
        
        # Result count label
        self.count_label = ttk.Label(filter_frame, text="", style="Muted.TLabel",
                                    font=("Segoe UI", 9))
        self.count_label.pack(side=tk.RIGHT, padx=8)
        
        # ── Treeview table ──
        table_frame = ttk.Frame(self, style="Panel.TFrame")
        table_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))
        
        # Treeview
        self.tree = ttk.Treeview(table_frame, columns=list(COLUMNS),
                                show="headings", selectmode="extended")
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Vertical scrollbar
        vsb = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.configure(yscrollcommand=vsb.set)
        
        # Horizontal scrollbar
        hsb = ttk.Scrollbar(self, orient=tk.HORIZONTAL, command=self.tree.xview)
        hsb.pack(fill=tk.X, padx=8)
        self.tree.configure(xscrollcommand=hsb.set)
        
        # Configure columns
        for col in COLUMNS:
            self.tree.heading(col, text=COLUMN_HEADINGS[col],
                            command=lambda c=col: self._sort_by(c))
            self.tree.column(col, width=COLUMN_WIDTHS.get(col, 100), minwidth=40)
        
        # Bind events
        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        self.tree.bind("<Double-1>", self._on_dbl_click)
        
        # Tag rendering for the tags column
        self.tree.tag_configure("keep", foreground=self.theme.colors["action_keep"])
        self.tree.tag_configure("delete", foreground=self.theme.colors["action_delete"])
        self.tree.tag_configure("archive", foreground=self.theme.colors["action_archive"])
        self.tree.tag_configure("review", foreground=self.theme.colors["action_review"])

    def set_results(self, results: list):
        """Set the full results list and refresh the display."""
        self._results = list(results)
        self._update_filter_options()
        self._apply_filters()

    def _update_filter_options(self):
        """Update filter dropdowns based on current results."""
        categories = set()
        for r in self._results:
            cat = r.get("category", "") if isinstance(r, dict) else getattr(r, "category", "")
            if cat:
                categories.add(cat)
        
        self.category_combo["values"] = ["All"] + sorted(categories)

    def _apply_filters(self, *_):
        """Apply all active filters and refresh the table."""
        filtered = list(self._results)
        
        # Search filter
        search = self.search_var.get().strip()
        if search:
            filtered = keyword_filter(filtered, search=search)
        
        # Category filter
        cat = self.category_var.get()
        if cat and cat != "All":
            filtered = [r for r in filtered if 
                       (isinstance(r, dict) and r.get("category") == cat) or
                       (hasattr(r, "category") and r.category == cat)]
        
        # Action filter
        action = self.action_var.get()
        if action and action != "All":
            filtered = [r for r in filtered if
                       (isinstance(r, dict) and r.get("action") == action) or
                       (hasattr(r, "action") and r.action == action)]
        
        # Lifecycle filter
        lifecycle = self.lifecycle_var.get()
        if lifecycle and lifecycle != "All":
            filtered = [r for r in filtered if
                       (isinstance(r, dict) and r.get("lifecycle") == lifecycle) or
                       (hasattr(r, "lifecycle") and r.lifecycle == lifecycle)]
        
        self._filtered = filtered
        self._populate_table()
        
        # Update count
        total = len(self._results)
        shown = len(filtered)
        if shown == total:
            self.count_label["text"] = f"{total} files"
        else:
            self.count_label["text"] = f"{shown} of {total} files"

    def _clear_filters(self):
        """Reset all filters to default."""
        self.search_var.set("")
        self.category_var.set("All")
        self.action_var.set("All")
        self.lifecycle_var.set("All")

    def _populate_table(self):
        """Fill the treeview with filtered results."""
        # Clear existing rows
        for row in self.tree.get_children():
            self.tree.delete(row)
        
        for entry in self._filtered:
            values = []
            tags = []
            
            for col in COLUMNS:
                if isinstance(entry, dict):
                    val = entry.get(col, "")
                else:
                    val = getattr(entry, col, "")
                
                # Format specific columns
                if col == "action":
                    icon = get_action_icon(str(val))
                    text = f" {icon} {val} "
                    tags.append(str(val).lower())
                elif col == "tags":
                    if isinstance(val, list):
                        text = " ".join(
                            t.split(":", 1)[1].replace("-", " ").title() if ":" in t else t
                            for t in val[:3]
                        )
                        if len(val) > 3:
                            text += f" +{len(val)-3}"
                    else:
                        text = str(val) if val else ""
                elif col == "confidence":
                    icon = get_confidence_icon(int(val) if val else 0)
                    text = f"{icon} {val}%"
                elif col == "category":
                    icon = get_category_icon(str(val))
                    text = f"{icon} {val}"
                else:
                    text = str(val) if val is not None else ""
                
                # Truncate long values
                if len(text) > 60:
                    text = text[:57] + "..."
                
                values.append(text)
            
            # Determine row tag for coloring
            action = entry.get("action", "").lower() if isinstance(entry, dict) else ""
            row_tag = action if action in ("keep", "delete", "archive", "review") else ""
            
            self.tree.insert("", tk.END, values=values, tags=(row_tag,) if row_tag else ())

    def _sort_by(self, col: str):
        """Sort the table by clicking a column heading."""
        if col == self._sort_column:
            self._sort_reverse = not self._sort_reverse
        else:
            self._sort_column = col
            self._sort_reverse = False
        
        # Sort the filtered list
        def sort_key(entry):
            if isinstance(entry, dict):
                val = entry.get(col, "")
            else:
                val = getattr(entry, col, "")
            
            # Handle numeric values
            if col in ("confidence", "importance"):
                try:
                    return float(val) if val else 0
                except (ValueError, TypeError):
                    return 0
            
            return str(val).lower()
        
        self._filtered.sort(key=sort_key, reverse=self._sort_reverse)
        
        # Update heading indicator
        arrow = " ▲" if not self._sort_reverse else " ▼"
        for c in COLUMNS:
            heading = COLUMN_HEADINGS[c]
            if c == col:
                heading += arrow
            self.tree.heading(c, text=heading)
        
        self._populate_table()

    def _on_select(self, event):
        """Handle selection change."""
        if self._on_selection_change:
            selected = self.get_selected()
            self._on_selection_change(selected)

    def _on_dbl_click(self, event):
        """Handle double-click on a row."""
        if self._on_double_click:
            selected = self.get_selected()
            if selected:
                self._on_double_click(selected[0])

    def get_selected(self) -> list:
        """Return the currently selected result entries."""
        selected_iids = self.tree.selection()
        if not selected_iids:
            return []
        
        # Map treeview items back to result entries
        result = []
        for iid in selected_iids:
            idx = self.tree.index(iid)
            if 0 <= idx < len(self._filtered):
                result.append(self._filtered[idx])
        
        return result

    def select_all(self):
        """Select all rows in the table."""
        self.tree.selection_set(self.tree.get_children())

    def clear_selection(self):
        """Clear the current selection."""
        self.tree.selection_set([])

    def get_all_displayed(self) -> list:
        """Return all currently displayed (filtered) results."""
        return list(self._filtered)