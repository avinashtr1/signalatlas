# SignalAtlas

Prediction market intelligence + execution system.

## Core Idea
System scans Polymarket, detects mispricing + liquidity vacuum, and executes trades based on expected edge.

## Architecture
Data → Intelligence → Brain → Execution → Analytics

Key modules:
- polymarket_engine/brain → decision logic
- polymarket_engine/execution → allocation + kill switch
- polymarket_engine/exit_engine.py → exit logic
- polymarket_engine/live_paper_loop.py → main loop

## Current Strategy (IMPORTANT)
- Passive execution
- Edge-based entry (expected_net_edge_pct)
- Exit:
  - EDGE_CAPTURE
  - PROFIT_TAKE
  - EDGE_DECAY
- Max open positions ≈ 20
- Basket-based deployment

## Known Issue
System lost profitability after exit logic + deployment changes post March 18.

Goal:
Restore March 17–18 profitable behavior.

## How to Run
python3 polymarket_engine/live_paper_loop.py

## Notes
- logs/ and analytics/ are excluded from repo
- execution truth is in logs/trades_closed.jsonl
- system is paper trading

