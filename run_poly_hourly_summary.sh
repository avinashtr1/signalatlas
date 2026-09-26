#!/usr/bin/env bash
set -euo pipefail

cd /root/.openclaw/workspace

while true; do
  PYTHONPATH=. python3 -m polymarket_engine.hourly_summary || true
  sleep 3600
done
