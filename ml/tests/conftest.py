"""Local conftest для ml/tests: добавляет ml/ в sys.path."""
from __future__ import annotations
from pathlib import Path
import sys

ML_DIR = Path(__file__).resolve().parent.parent
if str(ML_DIR) not in sys.path:
    sys.path.insert(0, str(ML_DIR))
