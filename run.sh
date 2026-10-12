#!/bin/zsh
set -euo pipefail
cd "$(dirname "$0")"
if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
.venv/bin/pip install -q -r requirements.txt
if [ ! -f assets/templates/media-partner.pptx ]; then
  echo "Building role templates from PDFs (first run)…"
  .venv/bin/python build_templates.py
fi
echo "Open http://127.0.0.1:8765"
open "http://127.0.0.1:8765"
exec .venv/bin/uvicorn app:app --host 127.0.0.1 --port 8765
