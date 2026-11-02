import os
import sys

# Put src/ on sys.path so plain `pytest` (no install step) passes.
sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "src")
)
