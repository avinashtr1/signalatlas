#!/usr/bin/env bash
set -euo pipefail

cd /root/.openclaw/workspace || exit 1

echo "=================================="
echo " SIGNALATLAS TOM MORNING PACK"
echo "=================================="
echo

echo "DASHBOARD:"
echo "  http://100.113.29.40:8022"
echo
echo "API:"
echo "  http://100.113.29.40:8011"
echo

echo "---- ops brief ----"
./tom_ops_brief.sh
echo

echo "---- deploy now ----"
./tom_deploy_now.sh
echo

echo "---- top quality ----"
./tom_top_quality.sh
echo

echo "---- quick service check ----"
systemctl is-active signalatlas-intelligence-api || true
systemctl is-active signalatlas-dashboard || true
echo

echo "=================================="
echo " SIGNALATLAS MORNING PACK COMPLETE"
echo "=================================="
