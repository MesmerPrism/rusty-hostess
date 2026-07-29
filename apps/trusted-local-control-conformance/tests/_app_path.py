"""Make the app-local package importable under repo-root unittest discovery."""

from __future__ import annotations

import sys
from pathlib import Path


APP_ROOT = Path(__file__).resolve().parents[1]
app_root_text = str(APP_ROOT)
if app_root_text not in sys.path:
    sys.path.insert(0, app_root_text)
