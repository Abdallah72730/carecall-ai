"""Pytest configuration — add backend root to sys.path so imports work."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
