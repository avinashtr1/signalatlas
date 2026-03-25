#!/usr/bin/env bash
set -euo pipefail
cd /root/.openclaw/workspace || exit 1

echo "SIGNALATLAS ALERT LOOP STARTED"

while true
do
    RADAR_SEND_TG=1 PYTHONPATH=. python3 -m polymarket_engine.radar_alert_engine
    sleep 60
done
