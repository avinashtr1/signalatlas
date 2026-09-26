#!/usr/bin/env bash
set -euo pipefail
cd /root/.openclaw/workspace || exit 1
PUBLIC_SEND_TG="${PUBLIC_SEND_TG:-0}" \
PUBLIC_FORCE_SEND="${PUBLIC_FORCE_SEND:-0}" \
PYTHONPATH=. python3 -m polymarket_engine.send_public_teaser
