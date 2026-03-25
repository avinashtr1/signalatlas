import json
from pathlib import Path
from datetime import datetime, timezone

LEADERBOARD_PATH = Path("analytics/alpha_leaderboard.json")
QUALITY_PATH = Path("analytics/alpha_quality_scores.json")
VACUUM_PATH = Path("analytics/liquidity_vacuum_v2.json")
MICRO_PATH = Path("analytics/microstructure_intelligence.json")
STALE_PATH = Path("analytics/stale_repricing.json")
MEMORY_PATH = Path("analytics/signal_memory.jsonl")
SUMMARY_PATH = Path("analytics/signal_memory_summary.json")

def load_json(path):
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))

def build_map(rows, key):
    out = {}
    for r in rows:
        k = r.get(key)
        if k:
            out[k] = r
    return out

def main():
    leaderboard = load_json(LEADERBOARD_PATH).get("leaderboard", [])
    quality_map = build_map(load_json(QUALITY_PATH).get("scores", []), "market_name")
    vacuum_map = build_map(load_json(VACUUM_PATH).get("vacuum_opportunities", []), "market_name")
    micro_map = build_map(load_json(MICRO_PATH).get("microstructure_signals", []), "market_name")
    stale_map = build_map(load_json(STALE_PATH).get("stale_repricing_opportunities", []), "market_name")

    ts = datetime.now(timezone.utc).isoformat()
    rows_written = 0

    with MEMORY_PATH.open("a", encoding="utf-8") as f:
        for r in leaderboard:
            market = r.get("market_name")
            q = quality_map.get(market, {})
            v = vacuum_map.get(market, {})
            m = micro_map.get(market, {})
            s = stale_map.get(market, {})

            payload = {
                "timestamp": ts,
                "market_name": market,
                "bucket": r.get("bucket_group_title"),
                "side": r.get("side"),
                "entry_price": float(r.get("entry_price", 0.0) or 0.0),
                "edge": float(r.get("total_edge", 0.0) or 0.0),
                "net_edge_pct": float(r.get("expected_net_edge_pct", 0.0) or 0.0),
                "fill_probability": float(r.get("expected_fill_probability", 1.0) or 1.0),
                "vacuum_score": float(r.get("vacuum_score", 0.0) or 0.0),
                "microstructure_score": float(r.get("microstructure_score", 0.0) or 0.0),
                "quality_score": float(q.get("quality_score", 0.0) or 0.0),
                "quality_grade": q.get("grade"),
                "vacuum_rank": float(v.get("vacuum_rank", 0.0) or 0.0),
                "micro_rank": float(m.get("micro_rank", 0.0) or 0.0),
                "stale_repricing_score": float(s.get("stale_repricing_score", 0.0) or 0.0),
                "flags": {
                    "is_deploy_now": False,
                    "has_quality": bool(q),
                    "has_vacuum": bool(v),
                    "has_micro": bool(m),
                    "has_stale": bool(s),
                }
            }

            f.write(json.dumps(payload) + "\n")
            rows_written += 1

    summary = {
        "timestamp": ts,
        "rows_written": rows_written,
        "memory_file": str(MEMORY_PATH),
    }
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print("SIGNALATLAS SIGNAL MEMORY")
    print(f"rows_written: {rows_written}")
    print("files created:")
    print("analytics/signal_memory.jsonl")
    print("analytics/signal_memory_summary.json")

if __name__ == "__main__":
    main()
