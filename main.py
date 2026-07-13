#!/usr/bin/env python3
"""
📎 Clippy Desktop Pet — WebEngine Edition
Uses clippyjs via HTML5 Canvas for smooth pixel-perfect rendering.

Usage:
  python main.py
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pet_window_web import main

if __name__ == "__main__":
    sys.exit(main())
