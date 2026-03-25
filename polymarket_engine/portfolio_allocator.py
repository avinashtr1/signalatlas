import json
from pathlib import Path
from datetime import datetime, timezone

RESOLUTION_PATH = Path("analytics/resolution_risk_report.json")
LEADERBOARD_PATH = Path("analytics/alpha_leaderboard.json")
OUT_JSON = Path("analytics/portfolio_allocator.json")
OUT_TXT = Path("analytics/portfolio_allocator.txt")

REFERENCE_EQUITY = 100000.0
MAX_TOTAL_DEPLOYMENT_PCT = 0.30   # max 30% deployed
MAX_SINGLE_POSITION_PCT = 0.02    # max 2% per position
BASE_RISK_UNIT_PCT = 0.005        # 0.5% base sizing

def load_json(path):
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))

def make_lookup(rows, key):
    out = {}
    for r in rows:
        k = r.get(key)
        if k:
            out[k] = r
    return out

def allocation_tier(efficiency):
    if efficiency >= 0.26:
        return ("A", 1.00)   # full allowed multiplier
    if efficiency >= 0.23:
        return ("B", 0.75)
    if efficiency >= 0.18:
        return ("C", 0.50)
    return ("D", 0.25)

def compute_allocations():
    res = load_json(RESOLUTION_PATH).get("markets", [])
    lb = load_json(LEADERBOARD_PATH).get("leaderboard", [])

    lb_by_market = make_lookup(lb, "market_name")

    rows = []
    deployed_pct = 0.0

    for r in res:
        market_name = r.get("market_name")
        lb_row = lb_by_market.get(market_name, {})

        edge = float(r.get("edge", 0.0) or 0.0)
        efficiency = float(r.get("capital_efficiency", 0.0) or 0.0)
        fill_prob = float(lb_row.get("expected_fill_probability", 1.0) or 1.0)
        vacuum = float(lb_row.get("vacuum_score", 0.0) or 0.0)
        micro = float(lb_row.get("microstructure_score", 0.0) or 0.0)

        tier, mult = allocation_tier(efficiency)

        # basic dynamic sizing model
        target_pct = BASE_RISK_UNIT_PCT
        target_pct *= mult
        target_pct *= fill_prob

        # reward stronger structural edge slightly
        if edge >= 0.13:
            target_pct *= 1.30
        elif edge >= 0.10:
            target_pct *= 1.15

        # reward vacuum opportunities slightly
        if vacuum >= 0.15:
            target_pct *= 1.10

        # small microstructure adjustment
        if micro < 0.03:
            target_pct *= 0.80

        # hard cap
        target_pct = min(target_pct, MAX_SINGLE_POSITION_PCT)

        # portfolio deployment cap
        remaining_pct = max(0.0, MAX_TOTAL_DEPLOYMENT_PCT - deployed_pct)
        final_pct = min(target_pct, remaining_pct)

        suggested_capital = REFERENCE_EQUITY * final_pct

        rows.append({
            "market_name": market_name,
            "bucket": r.get("bucket"),
            "edge": round(edge, 6),
            "efficiency": round(efficiency, 6),
            "fill_probability": round(fill_prob, 6),
            "allocation_tier": tier,
            "target_allocation_pct": round(final_pct, 6),
            "suggested_capital": round(suggested_capital, 2),
        })

        deployed_pct += final_pct

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "reference_equity": REFERENCE_EQUITY,
        "max_total_deployment_pct": MAX_TOTAL_DEPLOYMENT_PCT,
        "max_single_position_pct": MAX_SINGLE_POSITION_PCT,
        "total_allocated_pct": round(deployed_pct, 6),
        "total_allocated_capital": round(REFERENCE_EQUITY * deployed_pct, 2),
        "allocations": rows,
    }

def to_text(payload):
    lines = []
    lines.append("SIGNALATLAS DYNAMIC PORTFOLIO ALLOCATOR")
    lines.append("")
    lines.append(f"Reference Equity: {payload['reference_equity']:.2f}")
    lines.append(f"Total Allocated: {payload['total_allocated_capital']:.2f} ({payload['total_allocated_pct']*100:.2f}%)")
    lines.append("")

    allocs = payload.get("allocations", [])
    if not allocs:
        lines.append("No allocations computed.")
        return "\n".join(lines)

    for i, r in enumerate(allocs[:10], start=1):
        lines.append(
            f"{i}. {r['market_name']} | "
            f"tier={r['allocation_tier']} | "
            f"edge={r['edge']:.4f} | "
            f"eff={r['efficiency']:.4f} | "
            f"alloc={r['target_allocation_pct']*100:.2f}% | "
            f"capital={r['suggested_capital']:.2f}"
        )

    return "\n".join(lines)

def main():
    payload = compute_allocations()

    OUT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    OUT_TXT.write_text(to_text(payload), encoding="utf-8")

    print(to_text(payload))
    print("")
    print("files created:")
    print("analytics/portfolio_allocator.json")
    print("analytics/portfolio_allocator.txt")

if __name__ == "__main__":
    main()
