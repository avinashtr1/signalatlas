import json
from pathlib import Path
from datetime import datetime, timezone

SIG = Path("analytics/signal_memory.json")
SNAP = Path("analytics/market_snapshots.json")
OUT = Path("analytics/signal_outcomes.json")

# minimum move to count as meaningful follow-through
VALIDATE_MOVE = 0.02
FAIL_MOVE = -0.02

def load_json(p):
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))

def save_json(p, data):
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")

def parse_ts(x):
    try:
        return datetime.fromisoformat(x.replace("Z", "+00:00"))
    except Exception:
        return None

def main():
    sig_doc = load_json(SIG)
    snap_doc = load_json(SNAP)

    sig_rows = sig_doc.get("rows", [])
    snap_rows = snap_doc.get("rows", [])

    # latest snapshot per market
    latest_by_market = {}
    for r in snap_rows:
        name = r.get("market_name")
        ts = parse_ts(r.get("timestamp", ""))
        if not name or not ts:
            continue
        prev = latest_by_market.get(name)
        if prev is None or ts > prev["_ts"]:
            latest_by_market[name] = {"_ts": ts, **r}

    validated = 0
    failed = 0
    watching = 0
    out_rows = []

    for r in sig_rows:
        name = r.get("market_name")
        sig_ts = parse_ts(r.get("timestamp", ""))
        latest = latest_by_market.get(name)

        row = dict(r)
        row["evaluation_status"] = "watching"
        row["evaluation_move"] = None
        row["evaluation_timestamp"] = datetime.now(timezone.utc).isoformat()

        if latest and sig_ts:
            sig_prob = r.get("opportunity_score")
            cur_prob = latest.get("opportunity_score")

            try:
                sig_prob = float(sig_prob) if sig_prob is not None else None
                cur_prob = float(cur_prob) if cur_prob is not None else None
            except Exception:
                sig_prob = None
                cur_prob = None

            if sig_prob is not None and cur_prob is not None:
                move = cur_prob - sig_prob
                row["future_market_probability"] = cur_prob
                row["evaluation_move"] = round(move, 6)

                if move >= VALIDATE_MOVE:
                    row["evaluation_status"] = "validated"
                    row["outcome_pnl"] = round(move, 6)
                    validated += 1
                elif move <= FAIL_MOVE:
                    row["evaluation_status"] = "failed"
                    row["outcome_pnl"] = round(move, 6)
                    failed += 1
                else:
                    row["evaluation_status"] = "watching"
                    watching += 1
            else:
                watching += 1
        else:
            watching += 1

        out_rows.append(row)

    total_decided = validated + failed
    success_rate = round(validated / total_decided, 3) if total_decided > 0 else 0

    out = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "count": len(out_rows),
        "validated": validated,
        "failed": failed,
        "watching": watching,
        "success_rate": success_rate,
        "rows": out_rows,
    }

    save_json(OUT, out)

    print("OUTCOME ENGINE BUILT")
    print("file:", OUT)
    print("validated:", validated)
    print("failed:", failed)
    print("watching:", watching)
    print("success_rate:", success_rate)

if __name__ == "__main__":
    main()
