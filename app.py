# repo-root/app.py
# Minimal wrapper so gunicorn can import "app:app"
# It imports your real Flask app from backend.app and exposes it.

import importlib
import os
import sys

# Ensure 'backend' package path is resolvable (if backend is a directory)
ROOT = os.path.dirname(__file__)
BACKEND_PATH = os.path.join(ROOT, "backend")
if BACKEND_PATH not in sys.path:
    sys.path.insert(0, BACKEND_PATH)

# Import the backend module
# backend/app.py should define a Flask app object named `app`
try:
    # Option 1: If backend is a package (backend/__init__.py) you can use: from backend.app import app
    from backend import app as backend_module  # attempt to import as package
    # Try to use backend_module.app if available (handles both styles)
    app = getattr(backend_module, "app", None) or backend_module
except Exception:
    # Fallback: import by file path
    import importlib.util
    p = os.path.join(BACKEND_PATH, "app.py")
    spec = importlib.util.spec_from_file_location("backend_app", p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    app = getattr(m, "app", None)

if app is None:
    raise RuntimeError("Could not find Flask app object in backend/app.py. Make sure `app = Flask(__name__)` exists and is named `app`.")
