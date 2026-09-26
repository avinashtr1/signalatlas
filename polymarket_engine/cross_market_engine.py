import json
from pathlib import Path
from datetime import datetime, timezone

GRAPH = Path("analytics/market_graph.json")
MEM = Path("analytics/signal_memory.json")
OUT = Path("analytics/cross_market_signals.json")

# minimum contradiction gap to matter
MIN_EDGE = 0.08

def load_json(p):
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))

def save_json(p, data):
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")

def latest_by_market(rows):
    best = {}
    for r in rows:
        name = r.get("market_name")
        ts = r.get("timestamp", "")
        if not name:
            continue
        prev = best.get(name)
        if prev is None or ts > prev.get("timestamp", ""):
            best[name] = r
    return best

def to_float(x, default=None):
    try:
        if x is None or x == "":
            return default
        return float(x)
    except Exception:
        return default

def main():
    graph = load_json(GRAPH)
    mem = load_json(MEM)

    latest = latest_by_market(mem.get("rows", []))
    rels = graph.get("relationships", [])

    signals = []

    for rel in rels:
        parent = rel.get("parent_market")
        child = rel.get("child_market")
        strength = to_float(rel.get("strength"), 0.0)
        direction = rel.get("direction", "positive")

        p_row = latest.get(parent)
        c_row = latest.get(child)

        if not p_row or not c_row:
            continue

        p_prob = to_float(p_row.get("opportunity_score"))
        c_prob = to_float(c_row.get("opportunity_score"))

        if p_prob is None or c_prob is None:
            continue

        edge = 0.0
        contradiction = False
        reason = ""

        if direction == "positive":
            # child should usually not exceed parent by too much
            if c_prob > p_prob:
                edge = c_prob - p_prob
                contradiction = edge >= MIN_EDGE
                reason = "child_gt_parent"
        elif direction == "negative":
            # negative relation: both high together may be inconsistent
            if p_prob + c_prob > 1.0:
                edge = (p_prob + c_prob) - 1.0
                contradiction = edge >= MIN_EDGE
                reason = "negative_relation_violation"

        if contradiction:
            confidence = "HIGH" if edge >= 0.15 else "MEDIUM"
            signals.append({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "type": "cross_market_mispricing",
                "parent_market": parent,
                "child_market": child,
                "parent_score": round(p_prob, 6),
                "child_score": round(c_prob, 6),
                "edge": round(edge, 6),
                "strength": strength,
                "direction": direction,
                "confidence": confidence,
                "reason": reason,
            })

    out = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "count": len(signals),
        "signals": sorted(signals, key=lambda x: x["edge"], reverse=True),
    }

    save_json(OUT, out)

    print("CROSS MARKET ENGINE BUILT")
    print("file:", OUT)
    print("signals:", out["count"])

if __name__ == "__main__":
    main()
