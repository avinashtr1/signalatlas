# brain/scan.py
"""
Tom's Brain - Market Scanning Module

API Contract:
POST /scan/opportunities
Input: {
    "min_edge": 0.02,
    "min_liquidity": 1000,
    "clusters": ["crypto", "election"],
    "limit": 10
}

Output: {
    "opportunities": [
        {
            "id": "arb_001",
            "type": "ONE_OF_MANY",
            "cluster": "crypto",
            "edge": 0.05,
            "net_edge": 0.03,
            "legs": [...],
            "risk_score": 7,
            "discovered_at": "2026-02-19T04:43:00Z"
        }
    ],
    "total_scanned": 150,
    "found": 3,
    "scanned_at": "2026-02-19T04:43:00Z"
}
"""

from typing import Dict, List, Optional
from datetime import datetime

# Will be imported from scanner module
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def scan_opportunities(markets: List[Dict], filters: Dict = None) -> Dict:
    """
    Scan markets for arbitrage opportunities.
    Pure function - takes markets, returns opportunities.
    """
    filters = filters or {}
    
    min_edge = filters.get("min_edge", 0.02)
    min_liquidity = filters.get("min_liquidity", 1000)
    clusters = filters.get("clusters", [])
    limit = filters.get("limit", 10)
    
    # Import validate to use
    from brain.validate import validate_arb, MIN_EDGE
    
    opportunities = []
    scanned = 0
    
    # Group by cluster
    clusters_dict = {}
    for market in markets:
        cluster = market.get("cluster", "uncategorized")
        if clusters and cluster not in clusters:
            continue
        if cluster not in clusters_dict:
            clusters_dict[cluster] = []
        clusters_dict[cluster].append(market)
    
    # Scan each cluster
    for cluster_name, cluster_markets in clusters_dict.items():
        # Skip small clusters
        if len(cluster_markets) < 2:
            continue
        
        scanned += len(cluster_markets)
        
        # Validate for arb
        # Convert to validate format
        market_dicts = [
            {
                "id": m.get("id", m.get("market_id", f"mkt_{i}")),
                "question": m.get("question", ""),
                "outcome": m.get("outcome", "YES"),
                "price": float(m.get("price", m.get("probability", 0)))
            }
            for i, m in enumerate(cluster_markets)
        ]
        
        result = validate_arb(market_dicts, cluster_name)
        
        if result["is_arb"]:
            # Apply filters
            if result["net_edge_after_fees"] >= min_edge:
                # Calculate risk score (placeholder)
                risk_score = _calculate_risk_score(result)
                
                opportunities.append({
                    "id": f"arb_{cluster_name}_{len(opportunities)}",
                    "type": result["arb_type"],
                    "cluster": cluster_name,
                    "edge": result["edge"],
                    "net_edge": result["net_edge_after_fees"],
                    "legs": result["legs"],
                    "risk_score": risk_score,
                    "discovered_at": datetime.utcnow().isoformat() + "Z"
                })
    
    # Sort by edge (highest first)
    opportunities.sort(key=lambda x: x["net_edge"], reverse=True)
    
    # Apply limit
    opportunities = opportunities[:limit]
    
    return {
        "opportunities": opportunities,
        "total_scanned": scanned,
        "found": len(opportunities),
        "scanned_at": datetime.utcnow().isoformat() + "Z"
    }


def _calculate_risk_score(arb_result: Dict) -> int:
    """Calculate risk score 1-10 (higher = safer)."""
    score = 10
    
    # Deduct for risk flags
    flags = arb_result.get("risk_flags", [])
    score -= len(flags) * 2
    
    # Deduct for too many legs
    legs = arb_result.get("legs", [])
    if len(legs) > 3:
        score -= 1
    
    # Deduct for low edge
    if arb_result.get("net_edge_after_fees", 0) < 0.03:
        score -= 1
    
    return max(1, min(10, score))


# Standalone test
if __name__ == "__main__":
    # Mock markets
    markets = [
        {"id": "m1", "cluster": "crypto", "outcome": "YES", "price": 0.40, "question": "BTC $100k?"},
        {"id": "m2", "cluster": "crypto", "outcome": "YES", "price": 0.35, "question": "ETH $5k?"},
        {"id": "m3", "cluster": "crypto", "outcome": "YES", "price": 0.20, "question": "SOL $500?"},
        {"id": "m4", "cluster": "election", "outcome": "YES", "price": 0.50, "question": "Trump wins?"},
        {"id": "m5", "cluster": "election", "outcome": "YES", "price": 0.45, "question": "Biden wins?"}
    ]
    
    result = scan_opportunities(markets, {"min_edge": 0.02})
    print(result)
