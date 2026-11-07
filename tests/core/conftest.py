"""Laad de HA-onafhankelijke modules zonder custom_components/arthropoda/__init__.py.

Zo kunnen database, dagboek, caresheets en profielen getest worden zonder
dat Home Assistant geïnstalleerd is.
"""

import sys
import types
from pathlib import Path

PKG_DIR = Path(__file__).resolve().parents[2] / "custom_components" / "arthropoda"

pkg = types.ModuleType("arthropoda_core")
pkg.__path__ = [str(PKG_DIR)]
sys.modules["arthropoda_core"] = pkg
