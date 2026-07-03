"""
Main application window for AI File Manager GUI.

Orchestrates all panels: toolbar, dashboard, results table, detail panel,
query bar, and status bar. Manages scanning threads, dark mode, and
keyboard shortcuts.
"""

import os
import sys
import json
import threading
import csv
import io
from pathlib import Path
from datetime import datetime
from typing import Optional
from tkinter import filedialog, messagebox

import tkinter as tk
from tkinter import ttk

# Ensure project root is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gui.theme import ThemeManager
from gui.dashboard import DashboardPanel
from gui.results_panel import ResultsPanel
from gui.detail_panel import DetailPanel
from gui.query_panel import QueryPanel
from gui.context_menu import ContextMenu, show_in_explorer, copy_to_clipboard
from gui.widgets import ProgressOverlay, StatusBar, ToolbarButton
from gui.shortcuts import ShortcutManager
from gui.icons import (
    FOLDER, FILE, IMPORT, DARK_MODE, LIGHT_MODE, REFRESH,
    EXPORT, TRASH, SETTINGS, CLOSE
)

from scripts.analysis import scan_and_analyze, analyze_file
from scripts.query_engine import query_results, get_safe_to_delete
from scripts.similarity import find_similar_filenames
from scripts.reporter import save_batch_results
from scripts.cache import close as close_cache


class AIFileManagerApp:
    """
    Main application class. Owns the root window, theme, panels,
    and orchestrates all user interactions.
    """

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("AI File Manager")
        self.root.geometry("1400x850")
        self.root.minsize(1000, 600)

        # ── State ──
        self.results = []           # AnalysisResult objects
        self.errors = []
        self.current_path = ""
        self._scanning = False
        self._dashboard_visible = True

        # ── Theme ──
        self.theme = ThemeManager(root)

        # ── Shortcuts ──
        self.shortcuts = ShortcutManager(root)

        # ── Build UI ──
        self._build_menubar()
        self._build_layout()
        self._setup_shortcuts()
        self._setup_context_menu()

        # ── Status ──
        self.status_bar.set_status("Ready. Scan a folder to get started.")
        self._update_title()

        # ── Cleanup on close ──
        root.protocol("WM_DELETE_WINDOW", self.quit)

    # ─── Menu bar ────────────────────────────────────────────────────────────

    def _build_menubar(self):
        """Build the application menu bar."""
        menubar = tk.Menu(self.root, bg=self.theme.colors["panel_bg"],
                         fg=self.theme.colors["fg"],
                         activebackground=self.theme.colors["select_bg"],
                         activeforeground=self.theme.colors["select_fg"])

        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="📁 Scan Folder...    Ctrl+O", command=self.pick_folder)
        file_menu.add_command(label="📄 Analyze File...   Ctrl+N", command=self.pick_file)
        file_menu.add_command(label="📥 Load Reports...   Ctrl+L", command=self.load_reports)
        file_menu.add_separator()
        file_menu.add_command(label="📤 Export CSV...      Ctrl+E", command=self.export_csv)
        file_menu.add_separator()
        file_menu.add_command(label="✕ Quit                Ctrl+Q", command=self.quit)
        menubar.add_cascade(label="File", menu=file_menu)

        # View menu
        view_menu = tk.Menu(menubar, tearoff=0)
        view_menu.add_command(label="📊 Toggle Dashboard", command=self.toggle_dashboard)
        view_menu.add_command(label="🌙 Toggle Dark Mode  Ctrl+D", command=self.toggle_dark_mode)
        view_menu.add_separator()
        view_menu.add_command(label="⟳ Refresh (Re-scan) F5", command=self.refresh_scan)
        view_menu.add_separator()
        view_menu.add_command(label="⌨ Keyboard Shortcuts...", command=self.show_shortcuts)
        menubar.add_cascade(label="View", menu=view_menu)

        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="About AI File Manager", command=self.show_about)
        menubar.add_cascade(label="Help", menu=help_menu)

        self.root.config(menu=menubar)

    # ─── Layout ──────────────────────────────────────────────────────────────

    def _build_layout(self):
        """Build the three-panel layout with toolbar, progress, content, query, and status."""
        # Main vertical container
        main_container = ttk.Frame(self.root, style="Panel.TFrame")
        main_container.pack(fill=tk.BOTH, expand=True)

        # ── Toolbar ──
        toolbar = ttk.Frame(main_container, style="Panel.TFrame")
        toolbar.pack(fill=tk.X, padx=4, pady=4)

        ToolbarButton(toolbar, text="Scan Folder", icon=FOLDER,
                     command=self.pick_folder,
                     tooltip="Analyze all files in a folder").pack(side=tk.LEFT, padx=2)
        ToolbarButton(toolbar, text="Analyze File", icon=FILE,
                     command=self.pick_file,
                     tooltip="Analyze a single file").pack(side=tk.LEFT, padx=2)
        ToolbarButton(toolbar, text="Load Reports", icon=IMPORT,
                     command=self.load_reports,
                     tooltip="Load previously saved results").pack(side=tk.LEFT, padx=2)

        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=8, pady=2)

        ToolbarButton(toolbar, text="Refresh", icon=REFRESH,
                     command=self.refresh_scan,
                     tooltip="Re-scan current directory (F5)").pack(side=tk.LEFT, padx=2)
        ToolbarButton(toolbar, text="Export CSV", icon=EXPORT,
                     command=self.export_csv,
                     tooltip="Export results as CSV").pack(side=tk.LEFT, padx=2)

        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=8, pady=2)

        self.dark_mode_btn = ToolbarButton(toolbar, text="Dark Mode", icon=LIGHT_MODE,
                                          command=self.toggle_dark_mode,
                                          tooltip="Toggle dark/light theme")
        self.dark_mode_btn.pack(side=tk.LEFT, padx=2)

        # Spacer
        ttk.Label(toolbar, style="Panel.TFrame").pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Path display
        self.path_var = tk.StringVar()
        path_entry = ttk.Entry(toolbar, textvariable=self.path_var,
                              state="readonly", width=40)
        path_entry.pack(side=tk.RIGHT, padx=4)

        # ── Progress overlay ──
        self.progress_overlay = ProgressOverlay(main_container, self.theme)

        # ── Main content: PanedWindow with dashboard + results + detail ──
        content_frame = ttk.Frame(main_container, style="Panel.TFrame")
        content_frame.pack(fill=tk.BOTH, expand=True)

        # Dashboard (collapsible top region)
        self.dashboard = DashboardPanel(content_frame, self.theme)
        self.dashboard.pack(fill=tk.X)

        # Paned window for results + detail
        self.paned = ttk.PanedWindow(content_frame, orient=tk.HORIZONTAL)
        self.paned.pack(fill=tk.BOTH, expand=True)

        # Results panel (center, fills most of the space)
        self.results_panel = ResultsPanel(
            self.paned, self.theme,
            on_selection_change=self._on_selection_change,
            on_double_click=self._on_detail_request
        )
        self.paned.add(self.results_panel, weight=3)

        # Detail panel (right side)
        self.detail_panel = DetailPanel(self.paned, self.theme)
        self.paned.add(self.detail_panel, weight=1)

        # ── Query panel ──
        self.query_panel = QueryPanel(main_container, self.theme,
                                     on_query=self._on_query)
        self.query_panel.pack(fill=tk.X)

        # ── Status bar ──
        self.status_bar = StatusBar(main_container, self.theme)
        self.status_bar.pack(fill=tk.X)

    # ─── Shortcuts ───────────────────────────────────────────────────────────

    def _setup_shortcuts(self):
        """Set up keyboard shortcuts."""
        self.shortcuts.setup_defaults(self)

    # ─── Context menu ────────────────────────────────────────────────────────

    def _setup_context_menu(self):
        """Set up right-click context menu on the results table."""
        self.context_menu = ContextMenu(self.root, self.theme)
        self.context_menu.on_explain = self._explain_recommendation
        self.context_menu.on_find_similar = self._find_similar
        self.context_menu.on_show_in_explorer = self._show_in_explorer
        self.context_menu.on_copy_path = self._copy_path
        self.context_menu.on_mark_review = self._mark_review
        self.context_menu.on_export_entry = self._export_entry

        # Bind to results panel tree
        self.results_panel.tree.bind("<Button-3>", self._show_context_menu)

    def _show_context_menu(self, event):
        """Show context menu on right-click."""
        # Select the item under cursor
        item = self.results_panel.tree.identify_row(event.y)
        if item:
            self.results_panel.tree.selection_set(item)
            selected = self.results_panel.get_selected()
            if selected:
                self.context_menu.show(event, selected[0])

    # ─── Actions ─────────────────────────────────────────────────────────────

    def pick_folder(self):
        """Open folder picker and start batch scan."""
        path = filedialog.askdirectory(title="Select a folder to scan")
        if not path:
            return
        self._start_scan(path)

    def pick_file(self):
        """Open file picker and analyze single file."""
        path = filedialog.askopenfilename(title="Select a file to analyze")
        if not path:
            return
        self._start_single_scan(path)

    def load_reports(self):
        """Load a previously saved batch results JSON file."""
        path = filedialog.askopenfilename(
            title="Load batch results",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if not path:
            return

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load: {e}")
            return

        self.results = data.get("results", [])
        self.errors = data.get("error_details", [])
        self.current_path = data.get("directory", path)

        self.path_var.set(path)
        self._update_display()
        self.status_bar.set_status(f"Loaded {len(self.results)} results from {Path(path).name}.")
        self._update_title()

    def toggle_dark_mode(self):
        """Toggle between dark and light theme."""
        self.theme.toggle()
        icon = DARK_MODE if self.theme.is_dark else LIGHT_MODE
        text = "Light Mode" if self.theme.is_dark else "Dark Mode"
        self.dark_mode_btn.configure(text=f" {icon} {text}")

    def toggle_dashboard(self):
        """Toggle dashboard visibility."""
        if self._dashboard_visible:
            self.dashboard.pack_forget()
            self._dashboard_visible = False
        else:
            self.dashboard.pack(fill=tk.X, before=self.paned)
            self._dashboard_visible = True
            if self.results:
                self.dashboard.update(self.results)

    def refresh_scan(self):
        """Re-scan the current directory."""
        if self.current_path and os.path.isdir(self.current_path):
            self._start_scan(self.current_path)
        else:
            self.status_bar.set_status("No directory to re-scan. Use Scan Folder.")

    def export_csv(self):
        """Export results as CSV file."""
        if not self.results:
            messagebox.showinfo("Export", "No results to export.")
            return

        path = filedialog.asksaveasfilename(
            title="Export as CSV",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if not path:
            return

        try:
            # Determine fields from first result
            if isinstance(self.results[0], dict):
                fields = list(self.results[0].keys())
            else:
                fields = [f for f in dir(self.results[0]) if not f.startswith("_") and not callable(getattr(self.results[0], f))]

            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(fields)
                for entry in self.results:
                    if isinstance(entry, dict):
                        row = [str(entry.get(f, "")) for f in fields]
                    else:
                        row = [str(getattr(entry, f, "")) for f in fields]
                    writer.writerow(row)

            self.status_bar.set_status(f"Exported {len(self.results)} rows to {Path(path).name}.")
        except Exception as e:
            messagebox.showerror("Export Error", str(e))

    def focus_query(self):
        """Focus the query input bar."""
        self.query_panel.focus()

    def select_all(self):
        """Select all displayed results."""
        self.results_panel.select_all()

    def clear_selection(self):
        """Clear the current selection."""
        self.results_panel.clear_selection()

    def mark_for_deletion(self):
        """Mark selected files for deletion (visual flag only)."""
        selected = self.results_panel.get_selected()
        if selected:
            self.status_bar.set_status(f"Marked {len(selected)} files for review.")

    def show_detail(self):
        """Show detail for the first selected file."""
        selected = self.results_panel.get_selected()
        if selected:
            self._on_detail_request(selected[0])

    def preview_file(self):
        """Preview the first selected file."""
        selected = self.results_panel.get_selected()
        if selected:
            self._on_detail_request(selected[0])

    def clear_results(self):
        """Clear all results and reset the UI."""
        self.results = []
        self.errors = []
        self.current_path = ""
        self.path_var.set("")
        self.results_panel.set_results([])
        self.detail_panel.clear()
        self.dashboard.update([])
        self.status_bar.set_status("Cleared.")
        self.status_bar.clear_count()
        self._update_title()

    def quit(self):
        """Clean up and exit."""
        close_cache()
        self.root.quit()
        self.root.destroy()

    def show_shortcuts(self):
        """Show keyboard shortcuts dialog."""
        shortcuts = self.shortcuts.get_all_shortcuts()
        text = "Keyboard Shortcuts\n" + "=" * 30 + "\n\n"
        for key, desc in shortcuts:
            text += f"  {key:<20} {desc}\n"

        messagebox.showinfo("Keyboard Shortcuts", text)

    def show_about(self):
        """Show about dialog."""
        messagebox.showinfo(
            "About AI File Manager",
            "AI File Manager v0.3\n\n"
            "An intelligent file organization system that uses AI\n"
            "to analyze, categorize, and recommend actions for your files.\n\n"
            "Powered by Groq API"
        )

    # ─── Scanning ────────────────────────────────────────────────────────────

    def _start_scan(self, directory_path: str):
        """Start a batch scan in a background thread."""
        if self._scanning:
            return

        self._scanning = True
        self.current_path = directory_path
        self.path_var.set(directory_path)
        self.results = []
        self.errors = []
        self.results_panel.set_results([])
        self.detail_panel.clear()

        self.progress_overlay.show()
        self.status_bar.set_status(f"Scanning {Path(directory_path).name}...")

        def worker():
            try:
                results, errors, summary = scan_and_analyze(
                    directory_path,
                    progress_callback=self._on_scan_progress,
                    use_cache=True
                )
                self.results = [r.to_dict() for r in results]
                self.errors = errors

                self.root.after(0, self._on_scan_complete, summary)
            except Exception as e:
                self.root.after(0, lambda: self._on_scan_error(str(e)))
            finally:
                self._scanning = False

        threading.Thread(target=worker, daemon=True).start()

    def _start_single_scan(self, file_path: str):
        """Analyze a single file."""
        if self._scanning:
            return

        self._scanning = True
        self.current_path = file_path
        self.path_var.set(file_path)

        self.progress_overlay.show()
        self.progress_overlay.update_progress(1, 1, Path(file_path).name)
        self.status_bar.set_status(f"Analyzing {Path(file_path).name}...")

        def worker():
            try:
                analysis, raw, was_cached = analyze_file(file_path)

                if analysis is not None:
                    entry = {"file": Path(file_path).name, "path": file_path}
                    entry.update(analysis)
                    self.results = [entry]
                    self.errors = []

                    # Save individual result
                    try:
                        from scripts.reporter import save_ai_response
                        save_ai_response(file_path, raw)
                    except Exception:
                        pass

                    self.root.after(0, self._on_single_complete)
                else:
                    self.root.after(0, lambda: self._on_scan_error(raw))
            except Exception as e:
                self.root.after(0, lambda: self._on_scan_error(str(e)))
            finally:
                self._scanning = False

        threading.Thread(target=worker, daemon=True).start()

    def _on_scan_progress(self, progress):
        """Called from scanner thread with progress updates."""
        self.root.after(0, lambda: self.progress_overlay.update_progress(
            progress.current, progress.total, progress.current_file,
            cached=progress.cached, new_count=progress.scanned,
            errors=progress.errors
        ))

    def _on_scan_complete(self, summary):
        """Called when batch scan completes (main thread)."""
        self.progress_overlay.set_done(
            f"{summary.analyzed} files analyzed, {summary.cached} cached"
        )

        # Delay hiding so user sees completion
        self.root.after(2000, self.progress_overlay.hide)

        self._update_display()

        self.status_bar.set_status(
            f"Done. {summary.analyzed} analyzed ({summary.cached} cached), "
            f"{summary.errors} errors in {summary.duration_seconds:.1f}s"
        )
        self.status_bar.set_count(len(self.results))
        self._update_title()

        # Auto-save batch results
        try:
            saved = save_batch_results(
                self.results, self.errors, self.current_path, len(self.results)
            )
            self.status_bar.set_status(
                f"Done. {summary.analyzed} analyzed. Saved: {Path(saved).name}"
            )
        except Exception:
            pass

    def _on_single_complete(self):
        """Called when single file analysis completes."""
        self.progress_overlay.set_done("Analysis complete")
        self.root.after(1500, self.progress_overlay.hide)

        self._update_display()
        self.status_bar.set_status("Single file analysis complete.")
        self._update_title()

    def _on_scan_error(self, error: str):
        """Called when scan encounters an error."""
        self.progress_overlay.hide()
        self._scanning = False
        messagebox.showerror("Scan Error", error)
        self.status_bar.set_status(f"Error: {error}")

    def _update_display(self):
        """Update all panels with current results."""
        self.results_panel.set_results(self.results)
        self.dashboard.update(self.results)

    def _update_title(self):
        """Update window title with file count."""
        count = len(self.results)
        if count:
            self.root.title(f"AI File Manager - {count} files")
        else:
            self.root.title("AI File Manager")

    # ─── Selection handlers ──────────────────────────────────────────────────

    def _on_selection_change(self, selected):
        """Handle results table selection change."""
        if selected:
            self.detail_panel.show_file(selected[0])
        else:
            self.detail_panel.clear()

    def _on_detail_request(self, entry):
        """Handle double-click or Enter on a result."""
        # Show full JSON detail in a popup window
        if not entry:
            return

        if isinstance(entry, dict):
            text = json.dumps(entry, indent=2)
        else:
            text = json.dumps(entry.to_dict(), indent=2)

        win = tk.Toplevel(self.root)
        win.title(f"Details: {entry.get('file', 'Unknown') if isinstance(entry, dict) else entry.file}")
        win.geometry("600x500")
        win.minsize(400, 300)
        win.configure(bg=self.theme.colors["card_bg"])

        text_widget = tk.Text(win, wrap=tk.WORD, padx=12, pady=12,
                             font=("Consolas", 9),
                             bg=self.theme.colors["card_bg"],
                             fg=self.theme.colors["fg"])
        text_widget.pack(fill=tk.BOTH, expand=True)
        text_widget.insert(tk.END, text)
        text_widget.config(state=tk.DISABLED)

        scrollbar = ttk.Scrollbar(text_widget, command=text_widget.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        text_widget.config(yscrollcommand=scrollbar.set)

        ttk.Button(win, text="Close", command=win.destroy).pack(pady=8)

    # ─── Query handler ──────────────────────────────────────────────────────

    def _on_query(self, question: str):
        """Handle a query submission."""
        if not self.results:
            self.query_panel.show_error("No results to query.")
            return

        def worker():
            try:
                # Convert AnalysisResult objects to dicts
                results_dicts = []
                for r in self.results:
                    if hasattr(r, "to_dict"):
                        results_dicts.append(r.to_dict())
                    else:
                        results_dicts.append(r)

                response = query_results(results_dicts, question)
                answer = response.get("answer", "No answer.")
                matches = response.get("matching_files", [])

                text = answer
                if matches:
                    text += "\n\nMatching files:\n" + "\n".join(f"  • {f}" for f in matches)

                self.root.after(0, lambda: self.query_panel.show_result(text))
                self.root.after(0, lambda: self._show_query_result(text))
            except Exception as e:
                self.root.after(0, lambda: self.query_panel.show_error(str(e)))

        threading.Thread(target=worker, daemon=True).start()

    def _show_query_result(self, text: str):
        """Show query result in a popup window."""
        win = tk.Toplevel(self.root)
        win.title("Query Result")
        win.geometry("650x450")
        win.minsize(400, 250)
        win.configure(bg=self.theme.colors["card_bg"])

        text_widget = tk.Text(win, wrap=tk.WORD, padx=12, pady=12,
                             font=("Segoe UI", 10),
                             bg=self.theme.colors["card_bg"],
                             fg=self.theme.colors["fg"])
        text_widget.pack(fill=tk.BOTH, expand=True)
        text_widget.insert(tk.END, text)
        text_widget.config(state=tk.DISABLED)

        scrollbar = ttk.Scrollbar(text_widget, command=text_widget.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        text_widget.config(yscrollcommand=scrollbar.set)

        btn_frame = ttk.Frame(win, style="Card.TFrame")
        btn_frame.pack(fill=tk.X, pady=8)
        ttk.Button(btn_frame, text="Close", command=win.destroy).pack()

    # ─── Context menu handlers ──────────────────────────────────────────────

    def _explain_recommendation(self, entry):
        """Explain why a file received its recommendation."""
        reasoning = entry.get("reasoning", "") if isinstance(entry, dict) else getattr(entry, "reasoning", "")
        action = entry.get("action", "") if isinstance(entry, dict) else getattr(entry, "action", "")
        confidence = entry.get("confidence", 0) if isinstance(entry, dict) else getattr(entry, "confidence", 0)

        text = (
            f"Recommendation: {action}\n"
            f"Confidence: {confidence}%\n\n"
            f"Reasoning:\n{reasoning}\n\n"
            f"Suggested filename: {entry.get('suggested_filename', 'N/A') if isinstance(entry, dict) else getattr(entry, 'suggested_filename', 'N/A')}"
        )
        messagebox.showinfo("Explanation", text)

    def _find_similar(self, entry):
        """Find similar files in the current results."""
        filename = entry.get("file", "") if isinstance(entry, dict) else getattr(entry, "file", "")
        if not filename:
            return

        similar = find_similar_filenames(self.results, threshold=0.6)
        # Filter to only those involving the current file
        related = [(a, b, s) for a, b, s in similar
                   if (a.get("file") if isinstance(a, dict) else a.file) == filename
                   or (b.get("file") if isinstance(b, dict) else b.file) == filename]

        if related:
            text = f"Files similar to '{filename}':\n\n"
            for a, b, score in related:
                other = b if (a.get("file") if isinstance(a, dict) else a.file) == filename else a
                other_name = other.get("file") if isinstance(other, dict) else other.file
                text += f"  • {other_name} (score: {score:.1%})\n"
        else:
            text = f"No similar files found for '{filename}'."

        messagebox.showinfo("Similar Files", text)

    def _show_in_explorer(self, entry):
        """Open the file's location in Explorer."""
        path = entry.get("path", "") if isinstance(entry, dict) else getattr(entry, "path", "")
        if path:
            show_in_explorer(path)

    def _copy_path(self, entry):
        """Copy file path to clipboard."""
        path = entry.get("path", "") if isinstance(entry, dict) else getattr(entry, "path", "")
        if path:
            copy_to_clipboard(self.root, path)
            self.status_bar.set_status("Path copied to clipboard.")

    def _mark_review(self, entry):
        """Toggle the review flag on a file (visual only in current session)."""
        # Toggle in-memory
        if isinstance(entry, dict):
            entry["requires_review"] = not entry.get("requires_review", False)
            action = "marked for review" if entry["requires_review"] else "unmarked"
        else:
            entry.requires_review = not getattr(entry, "requires_review", False)
            action = "marked for review" if entry.requires_review else "unmarked"

        filename = entry.get("file", "Unknown") if isinstance(entry, dict) else getattr(entry, "file", "Unknown")
        self.status_bar.set_status(f"{filename} {action}.")

    def _export_entry(self, entry):
        """Export a single entry as JSON."""
        path = filedialog.asksaveasfilename(
            title="Export entry as JSON",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if not path:
            return

        try:
            if isinstance(entry, dict):
                data = entry
            else:
                data = entry.to_dict()

            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            self.status_bar.set_status(f"Entry exported to {Path(path).name}.")
        except Exception as e:
            messagebox.showerror("Export Error", str(e))