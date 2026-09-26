import json
from pathlib import Path
from datetime import datetime, timezone

EV = Path("analytics/expected_value.json")
OUT = Path("analytics/portfolio_allocator_v2.json")

REFERENCE_EQUITY = 100000.0
MAX_DEPLOY_PCT = 0.30
MAX_SINGLE_POS_PCT = 0.08

def load_json(p):
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))

def tier(score):
    if score >= 0.30:
        return "A"
    if score >= 0.18:
        return "B"
    if score >= 0.10:
        return "C"
    return "D"

def main():
    doc = load_json(EV)
    rows = doc.get("markets", [])

    positives = [r for r in rows if float(r.get("risk_adjusted_score", 0.0) or 0.0) > 0]
    total_score = sum(float(r.get("risk_adjusted_score", 0.0) or 0.0) for r in positives)

    max_capital = REFERENCE_EQUITY * MAX_DEPLOY_PCT
    allocations = []

    for r in positives:
        score = float(r.get("risk_adjusted_score", 0.0) or 0.0)
        pct = (score / total_score) if total_score > 0 else 0.0

        target_capital = pct * max_capital
        hard_cap = REFERENCE_EQUITY * MAX_SINGLE_POS_PCT
        suggested_capital = min(target_capital, hard_cap)
        alloc_pct = suggested_capital / REFERENCE_EQUITY

        allocations.append({
            "market_name": r.get("market_name"),
            "risk_adjusted_score": round(score, 6),
            "expected_value": round(float(r.get("expected_value", 0.0) or 0.0), 6),
            "expected_sharpe": round(float(r.get("expected_sharpe", 0.0) or 0.0), 6),
            "confidence_score": round(float(r.get("confidence_score", 0.0) or 0.0), 4),
            "recommended_action": r.get("recommended_action", "MONITOR"),
            "allocation_tier": tier(score),
            "target_allocation_pct": round(alloc_pct, 6),
            "suggested_capital": round(suggested_capital, 2),
        })

    allocations.sort(key=lambda x: x["suggested_capital"], reverse=True)

    total_alloc = sum(x["suggested_capital"] for x in allocations)
    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "reference_equity": REFERENCE_EQUITY,
        "max_deploy_pct": MAX_DEPLOY_PCT,
        "max_single_position_pct": MAX_SINGLE_POS_PCT,
        "total_allocated_capital": round(total_alloc, 2),
        "total_allocated_pct": round(total_alloc / REFERENCE_EQUITY, 6),
        "allocations": allocations,
    }

    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print("PORTFOLIO ALLOCATOR V2 BUILT")
    print("allocations:", len(allocations))
    print("file: analytics/portfolio_allocator_v2.json")

if __name__ == "__main__":
    main()
