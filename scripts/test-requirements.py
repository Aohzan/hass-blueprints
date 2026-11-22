"""Print the PyPI requirements of the integrations the tests set up.

pytest-homeassistant-custom-component installs Home Assistant core only:
integrations used by the blueprints (mobile_app imports cloud, camera...)
need their own requirements, read from the manifests of the installed
Home Assistant version and their dependencies.
"""

import json
from pathlib import Path

import homeassistant.components

INTEGRATIONS = ["mobile_app", "automation", "input_boolean", "input_datetime"]

components = Path(homeassistant.components.__file__).parent
seen: set[str] = set()
requirements: set[str] = set()
todo = list(INTEGRATIONS)
while todo:
    domain = todo.pop()
    if domain in seen or not (components / domain / "manifest.json").exists():
        continue
    seen.add(domain)
    manifest = json.loads((components / domain / "manifest.json").read_text())
    requirements.update(manifest.get("requirements", []))
    todo += manifest.get("dependencies", []) + manifest.get("after_dependencies", [])
print("\n".join(sorted(requirements)))
