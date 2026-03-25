"""
Inventory Management & Contract

Responsibility:
- Maintain authoritative state of balances and positions.
- Provide snapshots for decision making.
- Track exposure and limits.
"""
from typing import Dict, Any
import time

class Inventory:
    def __init__(self):
        # Configuration / Limits
        self.limits = {
            "min_free_usdc": 10.0,
            "max_trade_usdc": 100.0,
            "max_open_trades": 5,
            "max_exposure_usdc": 500.0
        }
        
        # Current State (Mocked for Paper)
        self.venues = {
            "polymarket": {
                "chain": "polygon",
                "address": "0xMockWallet...",
                "assets": {
                    "USDC": {"total": 1000.0, "locked": 0.0, "free": 1000.0}
                }
            }
        }
        
        self.state = {
            "open_trades_count": 0,
            "total_exposure_usdc": 0.0,
            "last_updated": int(time.time())
        }

    def get_snapshot(self) -> Dict[str, Any]:
        """Return full inventory contract snapshot."""
        return {
            "venues": self.venues,
            "limits": self.limits,
            "state": self.state,
            "timestamp": int(time.time())
        }

    def check_balance(self, asset: str, amount: float) -> bool:
        """Check if sufficient free balance exists."""
        # Simplified: Check Polymarket USDC
        balance = self.venues["polymarket"]["assets"].get(asset, {})
        free = balance.get("free", 0.0)
        return free >= (amount + self.limits["min_free_usdc"])

    def reserve_funds(self, asset: str, amount: float):
        """Lock funds for a trade (Paper simulation)."""
        if self.check_balance(asset, amount):
            self.venues["polymarket"]["assets"][asset]["free"] -= amount
            self.venues["polymarket"]["assets"][asset]["locked"] += amount
            self.state["total_exposure_usdc"] += amount
            self.state["open_trades_count"] += 1
            return True
        return False

# Global Singleton
inventory = Inventory()
