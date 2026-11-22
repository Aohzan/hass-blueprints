#!/usr/bin/env bash
# Run the blueprint tests in a virtualenv against a Home Assistant release.
#
# Environment:
#   PYTHON         Python version (default 3.14)
#   REQUIREMENTS   Requirements file pinning pytest-homeassistant-custom-component
#                  (default requirements_test.txt)
#   EXCLUDE_NEWER  Ignore packages published after this date, to resolve the
#                  dependencies as they were at that release (default: 7 days ago)
#   VENV           Virtualenv directory (default .venv)
# Extra arguments are passed to pytest.
set -euo pipefail

cd "$(dirname "$0")/.."

venv=$(realpath -m "${VENV:-.venv}")
exclude_newer=${EXCLUDE_NEWER:-$(date -u -d '7 days ago' +%Y-%m-%dT%H:%M:%SZ)}

uv venv --quiet --allow-existing --python "${PYTHON:-3.14}" "$venv"
export VIRTUAL_ENV="$venv"
uv pip install --quiet --exclude-newer "$exclude_newer" \
  --requirement "${REQUIREMENTS:-requirements_test.txt}"
"$venv/bin/python" -I scripts/test-requirements.py > "$venv/integrations.txt"
uv pip install --quiet --exclude-newer "$exclude_newer" \
  --requirement "$venv/integrations.txt"
exec "$venv/bin/python" -m pytest "$@"
