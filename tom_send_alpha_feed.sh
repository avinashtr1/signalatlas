#!/usr/bin/env bash
set -euo pipefail
cd /root/.openclaw/workspace || exit 1
ALPHA_SEND_TG="${ALPHA_SEND_TG:-0}" \
ALPHA_FORCE_SEND="${ALPHA_FORCE_SEND:-0}" \
PYTHONPATH=. python3 -m polymarket_engine.send_alpha_feed
