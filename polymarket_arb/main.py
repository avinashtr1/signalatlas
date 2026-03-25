#!/usr/bin/env python3
"""
Polymarket Arb Scanner - Main Entry Point

Runs the full pipeline:
1. Fetch markets
2. Cluster markets
3. Detect arbs
4. Tom evaluates (ACCEPT/REJECT)
5. Notify via Telegram (only on decision)
6. Log decisions
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
import argparse
from datetime import datetime

# Import modules
from scanner.fetcher import fetch_markets, filter_markets
from scanner.cluster import cluster_markets
from scanner.detector import find_arb_candidates
from brain.evaluate import evaluate_risk
from storage.ledger import init_ledger, log_decision, get_stats
from integrations.telegram_notify import notify_arb_decision, notify_scanner_alive, notify_error


# Config
SCAN_INTERVAL = 300  # 5 minutes
HEARTBEAT_CYCLES = 12  # Every hour (12 * 5min)
MIN_EDGE = 0.02  # 2% minimum edge


def run_pipeline(min_edge: float = 0.02, min_liquidity: int = 5000):
    """
    Run the full Polymarket arb pipeline.
    """
    print(f"\n{'='*50}")
    print(f"Polymarket Scanner - {datetime.utcnow().isoformat()}Z")
    print(f"{'='*50}")
    
    arbs_decided = 0
    
    try:
        # 1) Fetch markets
        print("\n[1] Fetching markets...")
        markets = fetch_markets()
        print(f"    Found {len(markets)} raw markets")
        
        # 2) Filter by liquidity
        markets = filter_markets(markets, min_liquidity)
        print(f"    After liquidity filter: {len(markets)}")
        
        if not markets:
            return 0
        
        # 3) Cluster
        print("\n[2] Clustering markets...")
        clusters = cluster_markets(markets)
        print(f"    Found {len(clusters)} clusters")
        
        # 4) Find arbs
        print("\n[3] Scanning for arbs...")
        candidates = find_arb_candidates(clusters, min_edge)
        print(f"    Found {len(candidates)} arb candidates")
        
        # 5) Tom evaluates each
        print("\n[4] Tom evaluating...")
        for c in candidates:
            # Get end_date from first leg's market
            end_date = None
            legs = c.get("validation", {}).get("legs", [])
            if legs and "market_id" in legs[0]:
                # Look up the market's end_date
                for m in markets:
                    if m.get("id") == legs[0].get("market_id"):
                        end_date = m.get("end_date")
                        break
            
            # Evaluate using new Brain logic
            eval_result = evaluate_risk(c, end_date_str=end_date)
            decision = eval_result["decision"]
            reasons = eval_result["reasons"]
            quote_instructions = eval_result.get("quote_instructions", [])
            risk_flags = eval_result.get("risk_flags", [])
            
            arbs_decided += 1
            
            # Log decision
            val = c.get("validation", {})
            log_decision(
                decision_type="arb_validate",
                source="polymarket",
                decision=decision,
                edge=val.get("net_edge_after_fees", 0),
                legs=len(val.get("legs", [])),
                reasons=reasons,
                risk_flags=risk_flags
            )
            
            # Send Telegram alert with decision and end_date
            print(f"    {c.get('cluster')}: {decision}")
            if decision == "ACCEPT":
                print(f"    >>> Generated {len(quote_instructions)} Maker Instructions:")
                # Log full scan summary details here if needed
                
            notify_arb_decision(c, decision, reasons, end_date_str=end_date)
        
        # 6) Stats
        print("\n[5] Stats:")
        try:
            stats = get_stats()
            print(f"    Total: {stats.get('total', 0)}, Approved: {stats.get('approved', 0)}")
        except Exception as e:
            print(f"    Stats error: {e}")
        
        return arbs_decided
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        notify_error(str(e))
        return 0


def main():
    """Main loop - scan every X minutes."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--loop", action="store_true", help="Run continuously")
    parser.add_argument("--interval", type=int, default=SCAN_INTERVAL, help="Scan interval in seconds")
    args = parser.parse_args()
    
    # Initialize
    init_ledger()
    
    print("=" * 60)
    print("Polymarket Arb Scanner v1.1")
    print("=" * 60)
    print(f"Mode: {'Continuous' if args.loop else 'Single run'}")
    print(f"Interval: {args.interval}s")
    print("Press Ctrl+C to stop")
    print("=" * 60)
    
    cycle = 0
    
    while True:
        cycle += 1
        print(f"\n=== CYCLE {cycle} ===")
        
        try:
            arbs_decided = run_pipeline()
            
            # Heartbeat every N cycles
            if cycle % HEARTBEAT_CYCLES == 0:
                notify_scanner_alive(cycle, arbs_decided)
                
        except Exception as e:
            print(f"Loop error: {e}")
            notify_error(str(e))
        
        if not args.loop:
            break
            
        print(f"\n💤 Sleeping {args.interval}s...")
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
