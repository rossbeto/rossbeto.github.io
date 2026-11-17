"""The scripts are standalone files, not a package: make them importable for their tests."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
