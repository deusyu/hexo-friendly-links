#!/usr/bin/env python3
"""
Entry point script for Hexo Friendly Links Generator.
This replaces the old generator/main.py file.
"""

import sys
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.main import main

if __name__ == "__main__":
    main() 