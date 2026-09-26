#!/usr/bin/env bash
set -euo pipefail
cd /root/.openclaw/workspace || exit 1
PYTHONPATH=. python3 -m polymarket_engine.agent_queries ops-brief
