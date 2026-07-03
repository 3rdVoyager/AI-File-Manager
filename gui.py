#!/usr/bin/env python3
"""
AI File Manager - Graphical User Interface (tkinter)

Launch with:  python gui.py
Or via main:  python main.py --gui

This is a thin launcher that delegates to the gui/ package.
"""

import sys
import os

# Ensure project root is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gui import main

if __name__ == "__main__":
    main()