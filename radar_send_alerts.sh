#!/usr/bin/env bash
set -euo pipefail
cd /root/.openclaw/workspace || exit 1

RADAR_SEND_TG="${RADAR_SEND_TG:-0}" \
RADAR_FORCE_SEND="${RADAR_FORCE_SEND:-0}" \
PYTHONPATH=. python3 -m polymarket_engine.radar_alert_engine
