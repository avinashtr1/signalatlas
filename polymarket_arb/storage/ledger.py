# storage/ledger.py
"""
Storage - Decision Ledger

Logs all Tom's decisions and outcomes for:
- Debugging
- Performance tracking
- Billing (later)
"""

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List

LEDGER_DIR = Path("/root/.openclaw/workspace/polymarket_arb/storage")
DECISIONS_FILE = LEDGER_DIR / "decisions.csv"
OUTCOMES_FILE = LEDGER_DIR / "outcomes.json"


def init_ledger():
    """Create ledger files if they don't exist."""
    LEDGER_DIR.mkdir(parents=True, exist_ok=True)
    
    if not DECISIONS_FILE.exists():
        with open(DECISIONS_FILE, "w") as f:
            writer = csv.DictWriter(f, fieldnames=[
                "timestamp", "type", "source", "decision", 
                "score", "edge", "legs", "reasons", "risk_flags"
            ])
            writer.writeheader()
    
    if not OUTCOMES_FILE.exists():
        with open(OUTCOMES_FILE, "w") as f:
            json.dump([], f)


def log_decision(decision_type: str, source: str, decision: str, 
                 score: float = 0, edge: float = 0, 
                 legs: int = 0, reasons: List[str] = None,
                 risk_flags: List[str] = None):
    """
    Log a Tom decision.
    
    decision_type: "risk_eval" | "arb_validate" | "scan"
    source: "binance" | "polymarket"
    decision: "APPROVE" | "REJECT" | "ACCEPT" | "REJECT"
    """
    reasons = reasons or []
    risk_flags = risk_flags or []
    
    row = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "type": decision_type,
        "source": source,
        "decision": decision,
        "score": score,
        "edge": edge,
        "legs": legs,
        "reasons": " | ".join(reasons),
        "risk_flags": ",".join(risk_flags)
    }
    
    with open(DECISIONS_FILE, "a") as f:
        writer = csv.DictWriter(f, fieldnames=row.keys())
        writer.writerow(row)
    
    return row


def log_outcome(arb_id: str, decision: str, result: str, pnl: float = 0):
    """Log outcome of an executed arb."""
    outcomes = []
    
    if OUTCOMES_FILE.exists():
        with open(OUTCOMES_FILE, "r") as f:
            outcomes = json.load(f)
    
    outcomes.append({
        "arb_id": arb_id,
        "decision": decision,
        "result": result,  # "won" | "lost" | "pending"
        "pnl": pnl,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    })
    
    with open(OUTCOMES_FILE, "w") as f:
        json.dump(outcomes, f, indent=2)


def get_stats(days: int = 7) -> Dict:
    """Get decision stats."""
    if not DECISIONS_FILE.exists():
        return {"total": 0, "approved": 0, "rejected": 0}
    
    decisions = []
    with open(DECISIONS_FILE, "r") as f:
        reader = csv.DictReader(f)
        decisions = list(reader)
    
    total = len(decisions)
    approved = len([d for d in decisions if d["decision"] in ["APPROVE", "ACCEPT"]])
    rejected = len([d for d in decisions if d["decision"] in ["REJECT"]])
    
    return {
        "total": total,
        "approved": approved,
        "rejected": rejected,
        "approval_rate": approved / total if total > 0 else 0
    }


if __name__ == "__main__":
    init_ledger()
    print("Ledger initialized")
    print(get_stats())
