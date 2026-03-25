#!/usr/bin/env bash
set -euo pipefail

cd /root/.openclaw/workspace || exit 1

echo "=============================="
echo " SIGNALATLAS TOM DAILY RUN"
echo "=============================="
echo

echo "---- pipeline ----"
./run_signalatlas_daily.sh
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

echo "---- tom telegram card ----"
TOM_SEND_TG="${TOM_SEND_TG:-0}" TOM_FORCE_SEND="${TOM_FORCE_SEND:-0}" ./tom_send_card.sh
echo

echo "=============================="
echo " SIGNALATLAS TOM DAILY COMPLETE"
echo "=============================="
