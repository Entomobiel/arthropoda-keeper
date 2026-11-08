"""Onderlinge JS-imports moeten de frontendversie dragen (cache-busting)."""

import json
import re
from pathlib import Path

COMP = Path(__file__).parents[2] / "custom_components" / "arthropoda"


def test_imports_carry_frontend_version():
    version = re.search(r'FRONTEND_VERSION = "([^"]+)"', (COMP / "const.py").read_text("utf-8")).group(1)
    assert json.loads((COMP / "manifest.json").read_text("utf-8"))["version"] == version
    found = 0
    for js in (COMP / "frontend").glob("*.js"):
        for target in re.findall(r'from "(\./[^"]+)"', js.read_text("utf-8")):
            found += 1
            assert target.endswith(f".js?v={version}"), (js.name, target)
    assert found >= 5
