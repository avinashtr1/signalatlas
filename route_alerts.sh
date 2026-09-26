#!/usr/bin/env bash
set -euo pipefail
cd /root/.openclaw/workspace || exit 1

ROUTE_DAILY_BRIEF="${ROUTE_DAILY_BRIEF:-1}" \
ROUTE_TOM_CARD="${ROUTE_TOM_CARD:-1}" \
ROUTE_ALPHA_FEED="${ROUTE_ALPHA_FEED:-0}" \
ROUTE_PUBLIC_TEASER="${ROUTE_PUBLIC_TEASER:-0}" \
PYTHONPATH=. python3 -m polymarket_engine.alert_router
