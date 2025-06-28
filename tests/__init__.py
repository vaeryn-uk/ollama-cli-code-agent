import os
import sys
import types

# Ensure package imports work without installing the project
ROOT = os.path.dirname(os.path.dirname(__file__))
SRC = os.path.join(ROOT, "src")
sys.path.insert(0, SRC)
