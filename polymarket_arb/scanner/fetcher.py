# scanner/fetcher.py
"""
Polymarket Scanner - Fetch Markets

API: Fetches markets from Polymarket (mock for now)
"""

from typing import List, Dict
import random
from datetime import datetime, timedelta


def fetch_markets() -> List[Dict]:
    """
    Fetch active markets from Polymarket.
    TODO: Replace with real API call.
    
    Returns: List of market dicts with:
        - id
        - question
        - outcome (YES/NO)
        - price (probability)
        - volume
        - liquidity
        - end_date
        - cluster (to be assigned)
    """
    
    # Mock data - replace with real Polymarket API
    markets = [
        # Crypto cluster
        {"id": "pm_btc_100k", "question": "Will BTC hit $100k by Dec 2026?", 
         "outcome": "YES", "price": 0.55, "volume": 250000, "liquidity": 80000, "end_date": "2026-12-31"},
        {"id": "pm_btc_100k_no", "question": "Will BTC hit $100k by Dec 2026?",
         "outcome": "NO", "price": 0.45, "volume": 250000, "liquidity": 80000, "end_date": "2026-12-31"},
        
        {"id": "pm_eth_5k", "question": "Will ETH hit $5000 by Dec 2026?",
         "outcome": "YES", "price": 0.40, "volume": 180000, "liquidity": 55000, "end_date": "2026-12-31"},
        {"id": "pm_eth_5k_no", "question": "Will ETH hit $5000 by Dec 2026?",
         "outcome": "NO", "price": 0.60, "volume": 180000, "liquidity": 55000, "end_date": "2026-12-31"},
        
        {"id": "pm_sol_1000", "question": "Will SOL hit $1000 by Dec 2026?",
         "outcome": "YES", "price": 0.35, "volume": 120000, "liquidity": 40000, "end_date": "2026-12-31"},
        {"id": "pm_sol_1000_no", "question": "Will SOL hit $1000 by Dec 2026?",
         "outcome": "NO", "price": 0.65, "volume": 120000, "liquidity": 40000, "end_date": "2026-12-31"},
        
        # Election cluster
        {"id": "pm_trump_2028", "question": "Will Trump win 2028 election?",
         "outcome": "YES", "price": 0.45, "volume": 500000, "liquidity": 200000, "end_date": "2028-11-01"},
        {"id": "pm_trump_2028_no", "question": "Will Trump win 2028 election?",
         "outcome": "NO", "price": 0.55, "volume": 500000, "liquidity": 200000, "end_date": "2028-11-01"},
        
        {"id": "pm_dem_2028", "question": "Will Democrat win 2028 election?",
         "outcome": "YES", "price": 0.48, "volume": 350000, "liquidity": 150000, "end_date": "2028-11-01"},
        {"id": "pm_dem_2028_no", "question": "Will Democrat win 2028 election?",
         "outcome": "NO", "price": 0.52, "volume": 350000, "liquidity": 150000, "end_date": "2028-11-01"},
        
        # Tech cluster
        {"id": "pm_nvidia_2000", "question": "Will NVDA hit $2000 in 2026?",
         "outcome": "YES", "price": 0.38, "volume": 90000, "liquidity": 35000, "end_date": "2026-12-31"},
        {"id": "pm_nvidia_2000_no", "question": "Will NVDA hit $2000 in 2026?",
         "outcome": "NO", "price": 0.62, "volume": 90000, "liquidity": 35000, "end_date": "2026-12-31"},
        
        {"id": "pm_ai_regulation", "question": "Will US pass major AI regulation in 2026?",
         "outcome": "YES", "price": 0.60, "volume": 75000, "liquidity": 28000, "end_date": "2026-12-31"},
        {"id": "pm_ai_regulation_no", "question": "Will US pass major AI regulation in 2026?",
         "outcome": "NO", "price": 0.40, "volume": 75000, "liquidity": 28000, "end_date": "2026-12-31"},
    ]
    
    return markets


def filter_markets(markets: List[Dict], min_liquidity: int = 1000) -> List[Dict]:
    """Filter markets by liquidity and active status."""
    return [
        m for m in markets 
        if m.get("liquidity", 0) >= min_liquidity
    ]


if __name__ == "__main__":
    markets = fetch_markets()
    print(f"Fetched {len(markets)} markets")
    
    # Filter
    filtered = filter_markets(markets, 10000)
    print(f"After filter: {len(filtered)} markets")
