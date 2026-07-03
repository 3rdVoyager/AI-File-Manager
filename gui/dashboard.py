"""
Dashboard panel for AI File Manager GUI.

Shows summary cards, action breakdown, category distribution,
confidence distribution, and quick-action buttons.
"""

import tkinter as tk
from tkinter import ttk
from typing import Optional

from gui.theme import ThemeManager
from gui.widgets import CardFrame
from gui.icons import (
    FILES, DUPLICATES, CLEANUP, CHART, DASHBOARD,
    get_category_icon, get_action_icon
)
from scripts.analysis import compute_dashboard


class DashboardPanel(ttk.Frame):
    """
    Dashboard panel with summary cards and statistics.
    
    Layout:
    ┌─────────────────────────────────────────────┐
    │  📊 Dashboard                               │
    │  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐      │
    │  │Files │ │Safe  │ │Review│ │Dupes │      │
    │  │  42  │ │  12  │ │   5  │ │   3  │      │
    │  └──────┘ └──────┘ └──────┘ └──────┘      │
    │  ┌──────────────┐ ┌──────────────────┐     │
    │  │ Action Breakdown │ │ Categories       │     │
    │  │ Keep: 20 █████  │ │ Programming: 15  │     │
    │  │ Delete: 12 ███  │ │ Documents: 10    │     │
    │  └──────────────┘ └──────────────────┘     │
    └─────────────────────────────────────────────┘
    """

    def __init__(self, parent, theme: ThemeManager):
        super().__init__(parent, style="Panel.TFrame")
        self.theme = theme
        self._results = []
        
        self._build_ui()

    def _build_ui(self):
        """Construct the dashboard layout."""
        # Header
        header = ttk.Frame(self, style="Panel.TFrame")
        header.pack(fill=tk.X, padx=16, pady=(12, 8))
        
        ttk.Label(header, text=f"{DASHBOARD} Dashboard",
                 style="Title.TLabel").pack(side=tk.LEFT)
        
        ttk.Label(header, text="Overview of your analyzed files",
                 style="Secondary.TLabel").pack(side=tk.LEFT, padx=(12, 0))
        
        # Separator
        ttk.Separator(self, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=12, pady=4)
        
        # Scrollable content area
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
        
        # Bind mousewheel for scrolling
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel, add="+")
        
        # ── Summary cards row ──
        self.cards_frame = ttk.Frame(self.scroll_frame, style="Panel.TFrame")
        self.cards_frame.pack(fill=tk.X, padx=16, pady=8)
        
        # Create 4 summary cards
        self.card_files = self._create_summary_card(
            self.cards_frame, f"{FILES} Total Files", "0", "")
        self.card_safe = self._create_summary_card(
            self.cards_frame, f"{CLEANUP} Safe to Delete", "0", "")
        self.card_review = self._create_summary_card(
            self.cards_frame, "⚠ Needs Review", "0", "")
        self.card_dupes = self._create_summary_card(
            self.cards_frame, f"{DUPLICATES} Duplicates", "0", "")
        
        # ── Two-column layout ──
        columns_frame = ttk.Frame(self.scroll_frame, style="Panel.TFrame")
        columns_frame.pack(fill=tk.BOTH, expand=True, padx=16, pady=8)
        
        # Left column: Action breakdown
        left_col = ttk.Frame(columns_frame, style="Panel.TFrame")
        left_col.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 8))
        
        self.action_card = CardFrame(left_col, self.theme, f"{CHART} Action Breakdown")
        self.action_card.pack(fill=tk.X)
        self.action_content = self.action_card.content
        
        # Right column: Categories
        right_col = ttk.Frame(columns_frame, style="Panel.TFrame")
        right_col.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(8, 0))
        
        self.category_card = CardFrame(right_col, self.theme, "📂 Top Categories")
        self.category_card.pack(fill=tk.X)
        self.category_content = self.category_card.content
        
        # ── Bottom: Confidence + Tags ──
        bottom_frame = ttk.Frame(self.scroll_frame, style="Panel.TFrame")
        bottom_frame.pack(fill=tk.X, padx=16, pady=8)
        
        # Confidence distribution
        conf_card = CardFrame(bottom_frame, self.theme, "🎯 Confidence Distribution")
        conf_card.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
        self.confidence_content = conf_card.content
        
        # Tag cloud
        tag_card = CardFrame(bottom_frame, self.theme, "🏷 Tags")
        tag_card.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(8, 0))
        self.tag_content = tag_card.content
        
        # ── Empty state ──
        self.empty_label = ttk.Label(
            self.scroll_frame,
            text="No data yet.\nScan a folder or load reports to see your dashboard.",
            style="Muted.TLabel",
            font=("Segoe UI", 12),
            justify=tk.CENTER
        )
        self.empty_label.pack(pady=40)
        
        # Show empty state initially
        self._show_empty(True)

    def _create_summary_card(self, parent, title: str, value: str, subtitle: str) -> ttk.Frame:
        """Create a summary statistic card."""
        card = tk.Frame(parent, bg=self.theme.colors["card_bg"],
                       highlightbackground=self.theme.colors["card_border"],
                       highlightthickness=1, padx=16, pady=12)
        card.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)
        
        ttk.Label(card, text=title, style="Secondary.TLabel",
                 font=("Segoe UI", 9)).pack()
        
        value_label = ttk.Label(card, text=value,
                               style="Title.TLabel",
                               font=("Segoe UI", 24, "bold"))
        value_label.pack(pady=(4, 0))
        
        sub_label = ttk.Label(card, text=subtitle, style="Muted.TLabel",
                            font=("Segoe UI", 8))
        sub_label.pack()
        
        # Store references for updating
        card.value_label = value_label
        card.sub_label = sub_label
        
        return card

    def _show_empty(self, empty: bool):
        """Toggle empty state visibility."""
        if empty:
            self.cards_frame.pack_forget()
            for child in self.action_content.winfo_children():
                child.destroy()
            for child in self.category_content.winfo_children():
                child.destroy()
            for child in self.confidence_content.winfo_children():
                child.destroy()
            for child in self.tag_content.winfo_children():
                child.destroy()
            self.empty_label.pack(pady=40)
        else:
            self.empty_label.pack_forget()
            self.cards_frame.pack(fill=tk.X, padx=16, pady=8)

    def update(self, results: list):
        """Update the dashboard with new analysis results."""
        self._results = results
        
        if not results:
            self._show_empty(True)
            return
        
        self._show_empty(False)
        
        data = compute_dashboard(results)
        
        # Update summary cards
        self.card_files.value_label["text"] = str(data.get("total_files", 0))
        self.card_safe.value_label["text"] = str(data.get("safe_to_delete", 0))
        self.card_review.value_label["text"] = str(data.get("needs_review", 0))
        
        # Duplicates count (from similarity module, computed separately)
        dup_count = data.get("duplicate_candidates", 0)
        self.card_dupes.value_label["text"] = str(dup_count)
        
        # Action breakdown
        for child in self.action_content.winfo_children():
            child.destroy()
        
        actions = data.get("action_breakdown", {})
        total = sum(actions.values()) or 1
        for action, count in sorted(actions.items(), key=lambda x: -x[1]):
            pct = int(count / total * 100)
            color = self.theme.get_action_color(action)
            icon = get_action_icon(action)
            
            row = ttk.Frame(self.action_content, style="Card.TFrame")
            row.pack(fill=tk.X, pady=2)
            
            ttk.Label(row, text=f"{icon} {action}", style="Card.TLabel",
                     font=("Segoe UI", 9)).pack(side=tk.LEFT)
            
            ttk.Label(row, text=str(count), style="Card.TLabel",
                     font=("Segoe UI", 9, "bold")).pack(side=tk.RIGHT)
            
            # Mini bar
            bar_frame = ttk.Frame(self.action_content, style="Card.TFrame")
            bar_frame.pack(fill=tk.X, pady=(0, 4))
            bar = tk.Frame(bar_frame, bg=color, height=4, width=pct * 3)
            bar.pack(side=tk.LEFT)
        
        # Categories
        for child in self.category_content.winfo_children():
            child.destroy()
        
        categories = data.get("categories", {})
        for cat, count in list(categories.items())[:8]:
            icon = get_category_icon(cat)
            row = ttk.Frame(self.category_content, style="Card.TFrame")
            row.pack(fill=tk.X, pady=1)
            
            ttk.Label(row, text=f"{icon} {cat}", style="Card.TLabel",
                     font=("Segoe UI", 9)).pack(side=tk.LEFT)
            ttk.Label(row, text=str(count), style="Card.TLabel",
                     font=("Segoe UI", 9)).pack(side=tk.RIGHT)
        
        # Confidence distribution
        for child in self.confidence_content.winfo_children():
            child.destroy()
        
        conf = data.get("confidence_distribution", {})
        conf_total = sum(conf.values()) or 1
        
        conf_items = [
            ("🟢 High (85-100)", conf.get("high", 0), self.theme.colors["success"]),
            ("🟡 Medium (60-84)", conf.get("medium", 0), self.theme.colors["warning"]),
            ("🔴 Low (0-59)", conf.get("low", 0), self.theme.colors["danger"]),
        ]
        
        for label, count, color in conf_items:
            pct = int(count / conf_total * 100)
            row = ttk.Frame(self.confidence_content, style="Card.TFrame")
            row.pack(fill=tk.X, pady=2)
            
            ttk.Label(row, text=label, style="Card.TLabel",
                     font=("Segoe UI", 9)).pack(side=tk.LEFT)
            ttk.Label(row, text=f"{count} ({pct}%)", style="Card.TLabel",
                     font=("Segoe UI", 9)).pack(side=tk.RIGHT)
            
            bar_frame = ttk.Frame(self.confidence_content, style="Card.TFrame")
            bar_frame.pack(fill=tk.X, pady=(0, 4))
            bar = tk.Frame(bar_frame, bg=color, height=4, width=pct * 3)
            bar.pack(side=tk.LEFT)
        
        # Tag cloud
        for child in self.tag_content.winfo_children():
            child.destroy()
        
        tags = data.get("tag_cloud", {})
        if tags:
            # Display as a flow of tag labels
            tag_frame = ttk.Frame(self.tag_content, style="Card.TFrame")
            tag_frame.pack(fill=tk.X, pady=4)
            
            for tag, count in list(tags.items())[:15]:
                display = tag.split(":", 1)[1].replace("-", " ").title() if ":" in tag else tag
                lbl = ttk.Label(tag_frame, text=f" {display} ({count}) ",
                              style="Card.TLabel",
                              font=("Segoe UI", 8))
                lbl.pack(side=tk.LEFT, padx=2, pady=1)
        else:
            ttk.Label(self.tag_content, text="No tags available",
                     style="Muted.TLabel").pack(pady=8)