#!/usr/bin/env bash
set -euo pipefail

cd /root/.openclaw/workspace || exit 1

echo "---- reputation export ----"
PYTHONPATH=. python3 -m polymarket_engine.reputation_export

echo "---- signal detection logger ----"
PYTHONPATH=. python3 -m polymarket_engine.signal_detection_logger

echo "---- full reputation report ----"
PYTHONPATH=. python3 -m polymarket_engine.signal_reputation_full

echo "---- alpha leaderboard ----"
PYTHONPATH=. python3 -m polymarket_engine.alpha_leaderboard

echo "---- market quality gate ----"
PYTHONPATH=. python3 -m polymarket_engine.market_quality_gate

echo "---- opportunity radar ----"
PYTHONPATH=. python3 -m polymarket_engine.opportunity_radar

echo "---- mispricing engine ----"
PYTHONPATH=. python3 -m polymarket_engine.mispricing_engine

echo "---- probability shock detector ----"
PYTHONPATH=. python3 -m polymarket_engine.probability_shock_detector

echo "---- probability drift engine ----"
PYTHONPATH=. python3 -m polymarket_engine.probability_drift_engine

echo "---- liquidity collapse detector ----"
PYTHONPATH=. python3 -m polymarket_engine.liquidity_collapse_detector

echo "---- liquidity vacuum v2 ----"
PYTHONPATH=. python3 -m polymarket_engine.liquidity_vacuum_v2

echo "---- cross market lag ----"
PYTHONPATH=. python3 -m polymarket_engine.cross_market_lag_detector

echo "---- resolution arbitrage ----"
PYTHONPATH=. python3 -m polymarket_engine.resolution_arbitrage_detector

echo "---- microstructure intelligence ----"
PYTHONPATH=. python3 -m polymarket_engine.microstructure_intelligence

echo "---- stale repricing ----"
PYTHONPATH=. python3 -m polymarket_engine.stale_repricing_detector

echo "---- signal memory ----"
PYTHONPATH=. python3 -m polymarket_engine.signal_memory

echo "---- signal memory analytics ----"
PYTHONPATH=. python3 -m polymarket_engine.signal_memory_analytics

echo "---- module scoring ----"
PYTHONPATH=. python3 -m polymarket_engine.module_scoring

echo "---- market bucket scoring ----"
PYTHONPATH=. python3 -m polymarket_engine.market_bucket_scoring

echo "---- adaptive weighting ----"
PYTHONPATH=. python3 -m polymarket_engine.adaptive_weighting

echo "---- adaptive composite score ----"
PYTHONPATH=. python3 -m polymarket_engine.adaptive_composite_score

echo "---- adaptive alpha feed ----"
PYTHONPATH=. python3 -m polymarket_engine.adaptive_alpha_feed

echo "---- resolution tracking ----"
PYTHONPATH=. python3 -m polymarket_engine.resolution_tracking

echo "---- performance analytics ----"
PYTHONPATH=. python3 -m polymarket_engine.performance_analytics

echo "---- alpha feed ----"
PYTHONPATH=. python3 -m polymarket_engine.alpha_feed_generator

echo "---- resolution risk model ----"
PYTHONPATH=. python3 -m polymarket_engine.resolution_risk_model

echo "---- alpha quality scoring ----"
PYTHONPATH=. python3 -m polymarket_engine.alpha_quality_scoring

echo "---- portfolio allocator ----"
PYTHONPATH=. python3 -m polymarket_engine.portfolio_allocator

echo "---- daily brief ----"
PYTHONPATH=. python3 -m polymarket_engine.daily_brief

echo "---- weekly brief ----"
PYTHONPATH=. python3 -m polymarket_engine.weekly_brief

echo "---- public feed formatter ----"
PYTHONPATH=. python3 -m polymarket_engine.public_feed_formatter


echo "---- auto settlement scan ----"
PYTHONPATH=. python3 -m polymarket_engine.auto_settlement_scanner

echo "---- settlement updater ----"
PYTHONPATH=. python3 -m polymarket_engine.settlement_updater

echo "---- performance analytics ----"
PYTHONPATH=. python3 -m polymarket_engine.performance_analytics


echo "---- executive brief ----"
PYTHONPATH=. python3 -m polymarket_engine.executive_brief

echo "---- telegram delivery ----"
SEND_TG="${SEND_TG:-0}" FORCE_SEND="${FORCE_SEND:-0}" PYTHONPATH=. python3 -m polymarket_engine.send_daily_brief

echo "signalatlas daily pipeline complete"
