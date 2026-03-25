"""
Tom's Brain - Evaluation & Decision Core (v2)

Responsibility:
- Orchestrate the decision pipeline:
  1. Construct Trade Plan
  2. Run Brain Gates
  3. Generate JSON Output
"""
from typing import Dict, Any
from datetime import datetime
from brain.inventory import inventory
from brain.gates import run_gates
from maker.quoter import generate_quotes

MIN_ANNUALIZED_EDGE = 0.20
MAX_DURATION_DAYS = 30

def evaluate_risk(candidate: Dict, end_date_str: str = None) -> Dict:
    """
    Master Evaluation Function.
    Returns fully structured API-ready decision.
    """
    # 1. Preliminary Data Prep
    val = candidate.get("validation", {})
    
    # Duration Logic
    days_to_res = 365
    if end_date_str:
        try:
            end = datetime.strptime(end_date_str, "%Y-%m-%d")
            delta = end - datetime.now()
            days_to_res = max(1, delta.days)
        except:
            pass
            
    # Calculate Annualized
    net_edge = val.get("net_edge_after_fees", 0)
    annualized = net_edge * (365 / days_to_res)
    
    # 2. Construct Trade Plan (Preliminary for sizing)
    # Default size $10 for safety until OB wired
    size_usd = 10.0 
    trade_plan = {
        "action": "BUY_ARB",
        "venues": ["polymarket"],
        "cost_estimate": size_usd,
        "legs": len(val.get("legs", []))
    }

    # 3. Run Brain Gates
    # (Check balances, limits, and hard profitability rules)
    gates_passed, gate_reason = run_gates(candidate, inventory, trade_plan)
    
    # 4. Additional Soft Logic (Evaluator specific)
    reasons = []
    decision = "REJECT"
    
    if not gates_passed:
        reasons.append(gate_reason)
    else:
        # Check Annualized/Duration specifically
        if days_to_res > MAX_DURATION_DAYS:
            decision = "REJECT"
            gate_reason = "DURATION_TOO_LONG"
            reasons.append(f"Duration: {days_to_res}d > {MAX_DURATION_DAYS}d")
        elif annualized < MIN_ANNUALIZED_EDGE:
            decision = "REJECT"
            gate_reason = "ANNUALIZED_TOO_LOW"
            reasons.append(f"Annualized: {annualized:.1%} < {MIN_ANNUALIZED_EDGE:.0%}")
        else:
            decision = "ACCEPT"
            reasons.append("ALL_GATES_PASSED")

    # 5. Generate Quote Instructions (If Accepted)
    quote_instructions = []
    if decision == "ACCEPT":
        try:
            quote_instructions = generate_quotes(candidate)
            # Update inventory (mock reservation)
            inventory.reserve_funds("USDC", size_usd)
        except Exception as e:
            decision = "REJECT"
            gate_reason = f"QUOTE_GEN_ERROR: {str(e)}"

    # 6. Construct Final Output
    return {
        "decision": decision,
        "reason_code": gate_reason,
        "reasons": reasons,
        "metrics": {
            "net_edge": net_edge,
            "annualized_edge": annualized,
            "days_to_res": days_to_res,
            "score": val.get("score", 0)
        },
        "trade_plan": trade_plan,
        "quote_instructions": quote_instructions,
        "inventory_snapshot": inventory.get_snapshot(),
        "evaluated_at": datetime.utcnow().isoformat() + "Z"
    }
