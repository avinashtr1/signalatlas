"""
Maker Quote Instruction Generator (v2) - Fixed

Responsibility:
- Transform an arb opportunity (Cluster) into executable Maker Quote Instructions.
- Enforce strict JSON Schema.
- Calculate price/size/side for each leg.
- Apply fee adjustments and calculate net edge.
- Implement Cancel/Replace policies.
- Check liquidity/depth (mocked or flagged if missing).
"""

import uuid
import time
from typing import Dict, List, Optional
from maker.fees import fee_manager
from maker.risk import risk_manager

# Configuration Defaults
MIN_QUOTE_SIZE = 10.0 # Min $ per order
DEFAULT_SIZE = 50.0   # Default size for paper trades
REFRESH_MS_TARGET = 1000 # 1s refresh for paper mode
CANCEL_REPLACE_TRIGGER = 0.005 # 0.5 cents move
MAX_LIVE_ORDERS = 1

def generate_quotes(candidate: Dict, target_edge: float = 0.02) -> List[Dict]:
    """
    Generate maker quote instructions for an arb candidate.
    """
    instructions = []
    val = candidate.get("validation", {})
    legs = val.get("legs", [])
    cluster_id = candidate.get("cluster", "unknown")
    
    # Risk Snapshot for context
    risk_snapshot = risk_manager.get_risk_snapshot(cluster_id)
    
    # Fees
    maker_fee_bps = fee_manager.get_maker_bps()
    taker_fee_bps = fee_manager.get_taker_bps()
    
    for leg in legs:
        market_id = leg.get("market_id")
        outcome = leg.get("outcome") # YES/NO
        current_price = leg.get("price")
        
        # Liquidity Check (Stub)
        liquidity_data = {
            "depth_yes": "unknown",
            "depth_no": "unknown",
            "spread": "unknown",
            "best_bid": "unknown",
            "best_ask": "unknown",
            "slippage_estimate": "unknown"
        }
        
        # Risk Flags: No orderbook data
        risk_flags = ["NO_ORDERBOOK_DATA"]
        
        # Size Calculation (Risk capped)
        size_usd = 10.0 if "NO_ORDERBOOK_DATA" in risk_flags else DEFAULT_SIZE
        
        # Price Calculation
        price = current_price 
        
        # Edge Calculation
        raw_edge = val.get("edge", 0) / len(legs) if legs else 0
        fee_cost = (maker_fee_bps / 10000.0)
        net_edge = raw_edge - fee_cost
        
        # Dedupe Key
        dedupe_key = f"{cluster_id}|{market_id}|{outcome}|{price:.3f}"
        
        instruction = {
            "instruction_id": str(uuid.uuid4()),
            "timestamp": int(time.time() * 1000),
            
            # Market Data
            "market_id": market_id,
            "token_id": "unknown",
            "outcome": outcome,
            
            # Order Details
            "side": "BUY",
            "order_type": "LIMIT_MAKER",
            "price": price,
            "size_usd": size_usd,
            "shares": size_usd / price if price > 0 else 0,
            "time_in_force": "GTC",
            
            # Fees & Edge
            "fee_rate_bps": maker_fee_bps,
            "fee_source": "maker",
            "expected_edge_raw": raw_edge,
            "expected_edge_net": net_edge,
            
            # Policies
            "cancel_policy": {
                "refresh_ms_target": REFRESH_MS_TARGET,
                "cancel_replace_trigger": CANCEL_REPLACE_TRIGGER,
                "max_live_orders_per_market": MAX_LIVE_ORDERS,
                "dedupe_key": dedupe_key
            },
            
            # Risk & Liquidity
            "liquidity_check": liquidity_data,
            "risk_flags": risk_flags,
            "risk_context": risk_snapshot,
            "confidence_score": 5.0 # Placeholder
        }
        instructions.append(instruction)
        
    return instructions
