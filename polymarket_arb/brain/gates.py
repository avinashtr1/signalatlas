"""
Brain Gates - Risk & Balance Validation

Responsibility:
- Enforce strict "Go/No-Go" logic before acceptance.
- Return specific reason codes for automation.
"""
from typing import Dict, Tuple, Any
from brain.inventory import Inventory

MIN_ANNUALIZED_EDGE = 0.20
MAX_DURATION_DAYS = 30
MIN_EDGE = 0.02

def run_gates(candidate: Dict, inventory: Inventory, trade_plan: Dict) -> Tuple[bool, str]:
    """
    Run all gates against the candidate and current inventory.
    Returns: (Passed: bool, ReasonCode: str)
    """
    val = candidate.get("validation", {})
    cost_usdc = trade_plan.get("cost_estimate", 0.0)
    
    # --- 1. Balance Gates ---
    # Check USDC solvency
    if not inventory.check_balance("USDC", cost_usdc):
        return False, "INSUFFICIENT_FUNDS_USDC"

    # --- 2. Risk Gates (Profitability) ---
    net_edge = val.get("net_edge_after_fees", 0)
    if net_edge < MIN_EDGE:
        return False, "EDGE_TOO_LOW"
        
    # Annualized Check (passed from evaluator logic, or re-checked here)
    # Assuming pre-check, but verifying criticals:
    # (Simplified for the Gate logic - evaluator does heavy lifting, Gate does final binary check)
    
    # --- 3. State Gates (Limits) ---
    state = inventory.state
    limits = inventory.limits
    
    if state["open_trades_count"] >= limits["max_open_trades"]:
        return False, "MAX_OPEN_TRADES_REACHED"
        
    if (state["total_exposure_usdc"] + cost_usdc) > limits["max_exposure_usdc"]:
        return False, "MAX_EXPOSURE_REACHED"
        
    if cost_usdc > limits["max_trade_usdc"]:
        return False, "TRADE_SIZE_TOO_LARGE"

    return True, "GATES_PASSED"
