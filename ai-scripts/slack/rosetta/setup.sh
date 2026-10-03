#!/usr/bin/env bash
# One-time environment setup for Rosetta dependencies
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

sudo rm -f /etc/apt/sources.list.d/yarn.list
sudo apt-get update || echo "WARNING: apt-get update reported errors; continuing anyway"

sudo apt-get install -y --no-install-recommends \
  libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz-subset0 shared-mime-info \
  fonts-dejavu-core fonts-noto-core fonts-noto-cjk fonts-noto-color-emoji || exit 1

python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt || exit 1

python3 - <<'PY' || { echo "WeasyPrint self-test FAILED"; exit 1; }
from weasyprint import HTML
HTML(string="<p>ok</p>").write_pdf()
print("WeasyPrint self-test passed")
PY
