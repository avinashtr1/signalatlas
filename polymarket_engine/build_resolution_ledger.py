import json
from pathlib import Path
from datetime import datetime, timezone

MEMORY = Path("analytics/signal_memory.jsonl")
OUTCOMES = Path("analytics/market_outcomes.json")
OUT = Path("analytics/resolution_ledger.json")

def load_json(path):
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))

def load_jsonl(path):
    rows = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except Exception:
                pass
    return rows

def infer_win(side, outcome):
    side = (side or "").upper()
    outcome = (outcome or "").upper()
    if side == "SHORT" and outcome == "NO":
        return True
    if side == "LONG" and outcome == "YES":
        return True
    return False

def main():
    mem = load_jsonl(MEMORY)
    outcomes = load_json(OUTCOMES).get("outcomes", {})

    rows = []
    for r in mem:
        market = r.get("market_name")
        outcome = outcomes.get(market)
        if not outcome:
            continue

        side = r.get("side")
        win = infer_win(side, outcome)
        pnl = 1 if win else -1

        rows.append({
            "timestamp": r.get("timestamp"),
            "market_name": market,
            "side": side,
            "entry_price": r.get("entry_price"),
            "total_edge": r.get("total_edge"),
            "expected_net_edge_pct": r.get("expected_net_edge_pct"),
            "quality_score": r.get("quality_score"),
            "vacuum_score": r.get("vacuum_score"),
            "microstructure_score": r.get("microstructure_score"),
            "stale_repricing_score": r.get("stale_repricing_score", 0),
            "resolution_arb_v2_score": r.get("resolution_arb_v2_score", 0),
            "collapse_v2_score": r.get("collapse_v2_score", 0),
            "shock_score": r.get("shock_score", 0),
            "adaptive_radar_score": r.get("adaptive_radar_score", 0),
            "radar_tier": r.get("radar_tier", "D"),
            "vacuum": (r.get("vacuum_score") or 0),
            "microstructure": (r.get("microstructure_score") or 0),
            "stale_repricing": (r.get("stale_repricing_score") or 0),
            "resolution_arb": bool((r.get("resolution_arb_v2_score") or 0) > 0),
            "collapse": bool((r.get("collapse_v2_score") or 0) > 0),
            "shock": bool((r.get("shock_score") or 0) > 0),
            "resolved": True,
            "outcome": outcome,
            "win": win,
            "pnl": pnl,
        })

    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "rows": rows,
        "resolved_count": len(rows),
    }
    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print("RESOLUTION LEDGER BUILT")
    print(f"resolved_rows: {len(rows)}")
    print("file created: analytics/resolution_ledger.json")

if __name__ == "__main__":
    main()
