#!/usr/bin/env bash
set -euo pipefail
cd /root/.openclaw/workspace || exit 1
SIGNALATLAS_API_BASE="${SIGNALATLAS_API_BASE:-http://127.0.0.1:8011}" \
SIGNALATLAS_API_KEY="${SIGNALATLAS_API_KEY:-sa_7f8c9d1a4b6e2f3c5d0a8e7b9c1d4f6a2v1i2}" \
TOM_SEND_TG="${TOM_SEND_TG:-0}" \
TOM_FORCE_SEND="${TOM_FORCE_SEND:-0}" \
PYTHONPATH=. python3 -m polymarket_engine.send_tom_card
