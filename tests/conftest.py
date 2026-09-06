import os
import sys

# Every backend module imports its siblings as bare module names
# (e.g. "import baseline"), so tests need backend/ on sys.path the
# same way running "python backend/app.py" would put it there.
BACKEND_DIR = os.path.join(os.path.dirname(__file__), "..", "backend")
sys.path.insert(0, os.path.abspath(BACKEND_DIR))
