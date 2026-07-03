# GUI package for AI File Manager

from gui.app import AIFileManagerApp

def main():
    """Launch the GUI application."""
    import tkinter as tk
    root = tk.Tk()
    app = AIFileManagerApp(root)
    root.mainloop()