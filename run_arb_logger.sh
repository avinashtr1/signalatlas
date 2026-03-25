#!/bin/bash

while true
do
  echo "Updating polymarket snapshot..."
  PYTHONPATH=/root/.openclaw/workspace python3 polymarket_engine/arb/polymarket_snapshot_builder.py

  echo "Running arb detector..."
  python3 polymarket_engine/arb/arb_detector.py

  sleep 30
done
