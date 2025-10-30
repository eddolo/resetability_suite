# ==========================================================
# __init__.py
# ----------------------------------------------------------
# Initializes the Resetability Control Suite Python package.
# This allows importing submodules like:
#   from python.ui_live import render_live_tab
# ==========================================================

import os
import sys
from pathlib import Path

# --- Ensure base path is on sys.path (for dynamic imports) ---
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

# --- Optional: version info ---
__version__ = "3.0.0"
__author__ = "Paolo Cappuccini"

# --- Helper reexports (optional for convenience) ---
try:
    from . import ui_analysis, ui_live, ui_montecarlo
except Exception:
    # Soft fail so Streamlit can hot-reload even if one module is being edited
    pass


# --- Clean import banner (optional aesthetic) ---
def _show_import_banner():
    if os.getenv("RESETABILITY_SILENT", "0") != "1":
        print("🧭 Resetability Control Suite package loaded (modular UI mode).")


_show_import_banner()
