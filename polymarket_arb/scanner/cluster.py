# scanner/cluster.py
"""
Polymarket Scanner - Cluster Markets

Groups related markets into clusters for arb detection.
"""

from typing import List, Dict


# Keywords for clustering
CLUSTER_KEYWORDS = {
    "crypto": ["btc", "bitcoin", "eth", "ethereum", "sol", "solana", "crypto", "coin"],
    "election_2028": ["election", "president", "trump", "biden", "democrat", "republican", "2028"],
    "tech": ["nvidia", "nvda", "ai", "openai", "google", "apple", "meta", "tesla", "tech"],
    "sports": ["superbowl", "nba", "world cup", "olympics", "sports", "football"],
    "economy": ["recession", "inflation", "fed", "rate", "gdp", "economy"],
}


def cluster_markets(markets: List[Dict]) -> List[Dict]:
    """
    Group markets into clusters based on question keywords.
    
    Returns: List of cluster dicts:
        {
            "name": "crypto",
            "markets": [...]
        }
    """
    clusters = {}
    
    for market in markets:
        question = market.get("question", "").lower()
        assigned = False
        
        # Find matching cluster
        for cluster_name, keywords in CLUSTER_KEYWORDS.items():
            if any(kw in question for kw in keywords):
                if cluster_name not in clusters:
                    clusters[cluster_name] = []
                clusters[cluster_name].append(market)
                assigned = True
                break
        
        # Uncategorized
        if not assigned:
            if "uncategorized" not in clusters:
                clusters["uncategorized"] = []
            clusters["uncategorized"].append(market)
    
    # Convert to list
    return [
        {"name": name, "markets": markets}
        for name, markets in clusters.items()
    ]


def get_clusters_summary(clusters: List[Dict]) -> Dict:
    """Get summary of clusters."""
    return {
        "total_clusters": len(clusters),
        "clusters": [
            {
                "name": c["name"],
                "market_count": len(c["markets"]),
                "outcomes": len(set(m.get("outcome", "") for m in c["markets"]))
            }
            for c in clusters
        ]
    }


if __name__ == "__main__":
    # Test
    from scanner.fetcher import fetch_markets
    
    markets = fetch_markets()
    clusters = cluster_markets(markets)
    
    print(f"Found {len(clusters)} clusters:")
    for c in clusters:
        print(f"  - {c['name']}: {len(c['markets'])} markets")
