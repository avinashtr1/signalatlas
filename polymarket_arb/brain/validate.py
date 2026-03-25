# brain/validate.py
"""
Tom's Brain - Arb Validation Module

API Contract:
POST /arb/validate
Input: {
    "markets": [
        {"id": "mkt1", "question": "Will BTC hit $100k?", "outcome": "YES", "price": 0.65},
        {"id": "mkt2", "question": "Will ETH hit $5k?", "outcome": "YES", "price": 0.40}
    ],
    "cluster": "crypto"
}

Output: {
    "is_arb": true|false,
    "arb_type": "MUST_HAPPEN|ONE_OF_MANY|NONE",
    "combined_prob": 0.95,
    "edge": 0.05,
    "net_edge_after_fees": 0.03,
    "legs": [...],
    "risk_flags": [],
    "reasons": [],
    "validated_at": "2026-02-19T04:43:00Z"
}
"""

from typing import Dict, List, Optional
from datetime import datetime

# Config
MIN_EDGE = 0.02  # 2% minimum edge
FEE_PER_LEG = 0.01  # 1% fee per leg estimate


def validate_arb(markets: List[Dict], cluster: str = "general") -> Dict:
    """
    Validate if a set of markets contains an arbitrage opportunity.
    Returns structured response for API.
    """
    reasons = []
    risk_flags = []
    
    if len(markets) < 2:
        return {
            "is_arb": False,
            "arb_type": "NONE",
            "combined_prob": 0,
            "edge": 0,
            "net_edge_after_fees": 0,
            "legs": [],
            "risk_flags": ["insufficient_markets"],
            "reasons": ["Need at least 2 markets"],
            "validated_at": datetime.utcnow().isoformat() + "Z"
        }
    
    # Get all YES prices
    yes_markets = []
    no_markets = []
    
    for m in markets:
        outcome = m.get("outcome", "").upper()
        price = float(m.get("price", 0))
        
        if outcome == "YES":
            yes_markets.append({"market": m, "price": price})
        elif outcome == "NO":
            no_markets.append({"market": m, "price": price})
    
    # Check for ONE_OF_MANY (sum of YES < 1)
    total_yes = sum(m["price"] for m in yes_markets)
    
    if len(yes_markets) >= 2:
        yes_edge = 1 - total_yes
        
        if yes_edge >= MIN_EDGE:
            return _build_arb_response(
                arb_type="ONE_OF_MANY",
                combined_prob=total_yes,
                edge=yes_edge,
                legs=yes_markets,
                reasons=[
                    f"One-of-many: {len(yes_markets)} YES outcomes sum to {total_yes:.2f}",
                    f"Edge: {yes_edge:.2%}"
                ],
                cluster=cluster
            )
    
    # Check for MUST_HAPPEN (sum of NO < 1)
    if len(no_markets) >= 2:
        total_no = sum(m["price"] for m in no_markets)
        no_edge = 1 - total_no
        
        if no_edge >= MIN_EDGE:
            return _build_arb_response(
                arb_type="MUST_HAPPEN",
                combined_prob=total_no,
                edge=no_edge,
                legs=no_markets,
                reasons=[
                    f"Must-happen: {len(no_markets)} NO outcomes sum to {total_no:.2f}",
                    f"Edge: {no_edge:.2%}"
                ],
                cluster=cluster
            )
    
    # No arb found
    return {
        "is_arb": False,
        "arb_type": "NONE",
        "combined_prob": total_yes if yes_markets else 0,
        "edge": 0,
        "net_edge_after_fees": 0,
        "legs": [],
        "risk_flags": ["no_arb_found"],
        "reasons": [
            f"YES sum: {total_yes:.2f} (need edge > {MIN_EDGE})",
            f"NO sum: {sum(m['price'] for m in no_markets):.2f}"
        ],
        "validated_at": datetime.utcnow().isoformat() + "Z"
    }


def _build_arb_response(arb_type: str, combined_prob: float, edge: float, 
                         legs: List[Dict], reasons: List[str], cluster: str) -> Dict:
    """Helper to build arb response with fees and risk checks."""
    
    num_legs = len(legs)
    fees = num_legs * FEE_PER_LEG
    net_edge = edge - fees
    
    risk_flags = []
    
    # Risk checks
    if net_edge < MIN_EDGE:
        risk_flags.append("low_net_edge")
        reasons.append(f"Net edge after fees: {net_edge:.2%}")
    
    if num_legs > 5:
        risk_flags.append("too_many_legs")
        reasons.append(f"Warning: {num_legs} legs increases execution risk")
    
    # Liquidity warning (placeholder)
    for leg in legs:
        price = leg.get("price", 0)
        if price > 0.90:
            risk_flags.append("high_price_liquidity")
            reasons.append(f"Warning: High price {price} may have low liquidity")
    
    return {
        "is_arb": True,
        "arb_type": arb_type,
        "combined_prob": round(combined_prob, 3),
        "edge": round(edge, 3),
        "net_edge_after_fees": round(net_edge, 3),
        "legs": [
            {
                "market_id": leg["market"].get("id"),
                "outcome": leg["market"].get("outcome"),
                "price": leg["price"]
            }
            for leg in legs
        ],
        "risk_flags": risk_flags,
        "reasons": reasons,
        "cluster": cluster,
        "validated_at": datetime.utcnow().isoformat() + "Z"
    }


# Standalone test
if __name__ == "__main__":
    # Test: ONE_OF_MANY
    markets = [
        {"id": "mkt1", "question": "BTC to $100k?", "outcome": "YES", "price": 0.40},
        {"id": "mkt2", "question": "ETH to $5k?", "outcome": "YES", "price": 0.35},
        {"id": "mkt3", "question": "SOL to $500?", "outcome": "YES", "price": 0.20}
    ]
    
    result = validate_arb(markets, "crypto")
    print("ONE_OF_MANY test:")
    print(result)
    print()
    
    # Test: MUST_HAPPEN
    markets2 = [
        {"id": "mkt1", "question": "BTC to $100k?", "outcome": "NO", "price": 0.60},
        {"id": "mkt2", "question": "ETH to $5k?", "outcome": "NO", "price": 0.35}
    ]
    
    result2 = validate_arb(markets2, "crypto")
    print("MUST_HAPPEN test:")
    print(result2)
