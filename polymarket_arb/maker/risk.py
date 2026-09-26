"""
Risk Management Module (Enhanced)

Responsibility:
- Enforce inventory limits per cluster/theme.
- Provide real-time risk snapshots.
"""

import os
import json
import time
from typing import Dict, List
from datetime import datetime

EXPOSURE_FILE = "/root/.openclaw/workspace/polymarket_arb/storage/exposure.json"

# Limits (Paper trading config)
MAX_TOTAL_EXPOSURE_USD = 5000.0  # Total capital deployed
MAX_CLUSTER_EXPOSURE_USD = 1000.0 # Max per single cluster/arb
MAX_CORRELATED_EXPOSURE_USD = 2500.0 # Max for correlated themes (e.g. Election)
MAX_DURATION_DAYS = 365 # Don't take bets resolving > 1 year out

class RiskManager:
    def __init__(self):
        self.exposure = self._load_exposure()

    def _load_exposure(self) -> Dict:
        if os.path.exists(EXPOSURE_FILE):
            try:
                with open(EXPOSURE_FILE, "r") as f:
                    return json.load(f)
            except:
                pass
        return {
            "total_usd": 0.0,
            "clusters": {}, # "cluster_id": amount
            "themes": {},   # "election": amount
            "open_positions": 0
        }

    def check_risk(self, candidate: Dict, quote_size_usd: float) -> List[str]:
        """
        Check if a candidate trade fits within risk limits.
        """
        reasons = []
        cluster_id = candidate.get("cluster", "unknown")
        # Extract theme from cluster (e.g. "election_2024" -> "election")
        theme = cluster_id.split("_")[0] if "_" in cluster_id else "misc"
        
        # 1. Total Exposure
        if self.exposure["total_usd"] + quote_size_usd > MAX_TOTAL_EXPOSURE_USD:
            reasons.append(f"Risk: Max total exposure exceeded ({self.exposure['total_usd']} + {quote_size_usd} > {MAX_TOTAL_EXPOSURE_USD})")

        # 2. Cluster Exposure
        current_cluster = self.exposure["clusters"].get(cluster_id, 0.0)
        if current_cluster + quote_size_usd > MAX_CLUSTER_EXPOSURE_USD:
            reasons.append(f"Risk: Max cluster exposure exceeded ({current_cluster} + {quote_size_usd} > {MAX_CLUSTER_EXPOSURE_USD})")

        # 3. Correlated Theme Exposure
        current_theme = self.exposure["themes"].get(theme, 0.0)
        if current_theme + quote_size_usd > MAX_CORRELATED_EXPOSURE_USD:
            reasons.append(f"Risk: Max theme '{theme}' exposure exceeded ({current_theme} + {quote_size_usd} > {MAX_CORRELATED_EXPOSURE_USD})")

        # 4. Duration Check (Stub)
        # Assuming end_date logic is handled upstream or passed in candidate metadata
        
        return reasons

    def get_risk_snapshot(self, cluster_id: str = None) -> Dict:
        """
        Return current risk metrics for a given cluster.
        """
        theme = cluster_id.split("_")[0] if cluster_id and "_" in cluster_id else "misc"
        
        return {
            "total_exposure_usd": self.exposure["total_usd"],
            "cluster_exposure_usd": self.exposure["clusters"].get(cluster_id, 0.0),
            "theme_exposure_usd": self.exposure["themes"].get(theme, 0.0),
            "limits": {
                "max_total": MAX_TOTAL_EXPOSURE_USD,
                "max_cluster": MAX_CLUSTER_EXPOSURE_USD,
                "max_theme": MAX_CORRELATED_EXPOSURE_USD,
                "max_duration": MAX_DURATION_DAYS
            },
            "timestamp": int(time.time() * 1000)
        }

# Singleton
risk_manager = RiskManager()
