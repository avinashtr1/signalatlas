# scanner/detector.py
"""
Polymarket Scanner - Detect Arbitrages

Finds arb opportunities within clusters.
"""

from typing import List, Dict
from brain.validate import validate_arb, MIN_EDGE


def find_arb_candidates(clusters: List[Dict], min_edge: float = MIN_EDGE) -> List[Dict]:
    """
    Scan clusters for arbitrage opportunities.
    
    Returns: List of arb candidates with validation results.
    """
    candidates = []
    
    for cluster in clusters:
        cluster_name = cluster.get("name", "unknown")
        markets = cluster.get("markets", [])
        
        if len(markets) < 2:
            continue
        
        # Prepare markets for validation
        market_dicts = [
            {
                "id": m.get("id", ""),
                "question": m.get("question", ""),
                "outcome": m.get("outcome", "YES"),
                "price": float(m.get("price", m.get("probability", 0)))
            }
            for m in markets
        ]
        
        # Validate
        result = validate_arb(market_dicts, cluster_name)
        
        if result["is_arb"] and result["net_edge_after_fees"] >= min_edge:
            candidates.append({
                "cluster": cluster_name,
                "validation": result
            })
    
    # Sort by edge
    candidates.sort(key=lambda x: x["validation"].get("net_edge_after_fees", 0), reverse=True)
    
    return candidates


def format_candidates_for_telegram(candidates: List[Dict]) -> str:
    """Format arb candidates for Telegram notification."""
    if not candidates:
        return "No arbitrage opportunities found."
    
    lines = ["🎯 ARB OPPORTUNITIES FOUND:", ""]
    
    for i, c in enumerate(candidates[:5], 1):
        val = c["validation"]
        lines.append(f"{i}. {c['cluster'].upper()}")
        lines.append(f"   Type: {val['arb_type']}")
        lines.append(f"   Edge: {val['net_edge_after_fees']:.1%}")
        lines.append(f"   Legs: {len(val['legs'])}")
        if val.get("risk_flags"):
            lines.append(f"   ⚠️ {', '.join(val['risk_flags'])}")
        lines.append("")
    
    return "\n".join(lines)


if __name__ == "__main__":
    # Test
    from scanner.fetcher import fetch_markets
    from scanner.cluster import cluster_markets
    
    markets = fetch_markets()
    clusters = cluster_markets(markets)
    candidates = find_arb_candidates(clusters)
    
    print(f"Found {len(candidates)} arb candidates")
    for c in candidates:
        print(c["cluster"], c["validation"]["arb_type"], c["validation"]["net_edge_after_fees"])
