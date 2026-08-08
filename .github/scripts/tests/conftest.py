"""Make the sibling validator scripts importable as plain modules under test,
without turning .github/scripts into a package (it isn't one, and the lint.yml
workflow invokes each script directly with `python3 .github/scripts/x.py`)."""

import pathlib
import sys

SCRIPTS_DIR = pathlib.Path(__file__).resolve().parent.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))
