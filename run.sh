#!/usr/bin/env bash
# One-command local run (without Docker): creates .venv, installs pinned deps, runs tests + pipeline.
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -m venv .venv
. .venv/bin/activate
pip install --no-deps -r requirements.txt
python -m unittest discover -s tests
python src/benchmark.py --config "${1:-configs/config.yaml}"
