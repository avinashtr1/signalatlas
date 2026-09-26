#!/usr/bin/env bash
set -euo pipefail

cd /root/.openclaw/workspace || exit 1

echo "SYSTEM MONITOR STARTED"

while true
do
  PYTHONPATH=. python3 -m polymarket_engine.system_monitor
  sleep 60
done
