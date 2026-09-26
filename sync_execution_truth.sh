#!/bin/bash
set -e

SRC="analytics/execution_truth.json"
DST1="signalatlas_dashboard/execution_truth.json"
DST2="signalatlas_internal_console/execution_truth.json"

[ -f "$SRC" ] || { echo "missing $SRC"; exit 1; }

cp "$SRC" "$DST1"
[ -d "signalatlas_internal_console" ] && cp "$SRC" "$DST2" || true

echo "synced execution_truth.json"
