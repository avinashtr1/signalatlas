import csv
import json
from collections import defaultdict, Counter
from pathlib import Path

OPEN_LOG = Path("logs/trades_open.jsonl")
CLOSED_LOG = Path("logs/trades_closed.jsonl")
CYCLE_LOG = Path("logs/cycle_audit.jsonl")
OUTDIR = Path("desk_exports")


def load_jsonl(path: Path):
    rows = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k) for k in fieldnames})


def latest_open_positions(open_rows, closed_rows):
    closed_ids = {r.get("trade_id") for r in closed_rows}
    latest = {}
    for r in open_rows:
        tid = r.get("trade_id")
        if tid and tid not in closed_ids:
            latest[tid] = r
    return list(latest.values())


def main():
    OUTDIR.mkdir(parents=True, exist_ok=True)

    open_rows = load_jsonl(OPEN_LOG)
    closed_rows = load_jsonl(CLOSED_LOG)
    cycle_rows = load_jsonl(CYCLE_LOG)
    open_positions = latest_open_positions(open_rows, closed_rows)

    # trade journal
    journal_rows = []
    close_by_id = {r.get("trade_id"): r for r in closed_rows}
    for o in open_rows:
        tid = o.get("trade_id")
        c = close_by_id.get(tid, {})
        journal_rows.append({
            "trade_id": tid,
            "open_ts": o.get("ts"),
            "close_ts": c.get("ts"),
            "status": "CLOSED" if tid in close_by_id else "OPEN",
            "bucket_group_id": o.get("bucket_group_id"),
            "bucket_group_title": o.get("bucket_group_title"),
            "market_id": o.get("market_id"),
            "market_name": o.get("market_name"),
            "side": o.get("side"),
            "entry_price": o.get("entry_price"),
            "filled_size_usd": o.get("filled_size_usd"),
            "allocated_capital": o.get("allocated_capital"),
            "structural_edge": o.get("structural_edge"),
            "vacuum_score": o.get("vacuum_score"),
            "vacuum_reason": o.get("vacuum_reason"),
            "microstructure_score": o.get("microstructure_score"),
            "microstructure_reasons": o.get("microstructure_reasons"),
            "resolution_score": o.get("resolution_score"),
            "resolution_reason": o.get("resolution_reason"),
            "total_edge": o.get("total_edge"),
            "rank_score": o.get("rank_score"),
            "realized_pnl": c.get("realized_pnl"),
        })

    write_csv(
        OUTDIR / "trade_journal.csv",
        journal_rows,
        [
            "trade_id","open_ts","close_ts","status","bucket_group_id","bucket_group_title",
            "market_id","market_name","side","entry_price","filled_size_usd","allocated_capital",
            "structural_edge","vacuum_score","vacuum_reason","microstructure_score",
            "microstructure_reasons","resolution_score","resolution_reason","total_edge",
            "rank_score","realized_pnl"
        ]
    )

    # open positions
    write_csv(
        OUTDIR / "open_positions.csv",
        open_positions,
        [
            "ts","trade_id","bucket_group_id","bucket_group_title","market_id","market_name",
            "side","entry_price","filled_size_usd","allocated_capital","structural_edge",
            "vacuum_score","vacuum_reason","microstructure_score","microstructure_reasons",
            "resolution_score","resolution_reason","total_edge","rank_score"
        ]
    )

    # bucket summary
    by_bucket = defaultdict(list)
    for r in open_positions:
        by_bucket[r.get("bucket_group_title") or "NO_BUCKET"].append(r)

    bucket_rows = []
    for bucket, rows in by_bucket.items():
        bucket_rows.append({
            "bucket": bucket,
            "legs": len(rows),
            "capital": round(sum(float(x.get("allocated_capital", 0.0) or 0.0) for x in rows), 4),
            "avg_total_edge": round(sum(float(x.get("total_edge", 0.0) or 0.0) for x in rows) / max(len(rows), 1), 6),
            "avg_structural_edge": round(sum(float(x.get("structural_edge", 0.0) or 0.0) for x in rows) / max(len(rows), 1), 6),
            "avg_vacuum_score": round(sum(float(x.get("vacuum_score", 0.0) or 0.0) for x in rows) / max(len(rows), 1), 6),
            "avg_micro_score": round(sum(float(x.get("microstructure_score", 0.0) or 0.0) for x in rows) / max(len(rows), 1), 6),
            "avg_resolution_score": round(sum(float(x.get("resolution_score", 0.0) or 0.0) for x in rows) / max(len(rows), 1), 6),
        })

    write_csv(
        OUTDIR / "bucket_summary.csv",
        bucket_rows,
        ["bucket","legs","capital","avg_total_edge","avg_structural_edge","avg_vacuum_score","avg_micro_score","avg_resolution_score"]
    )

    # cycle audit raw export
    if cycle_rows:
        (OUTDIR / "cycle_audit_latest.json").write_text(json.dumps(cycle_rows[-1], indent=2), encoding="utf-8")
        (OUTDIR / "cycle_audit_count.txt").write_text(str(len(cycle_rows)), encoding="utf-8")

    # leaderboard export
    latest_loop = None
    for row in reversed(cycle_rows):
        if row.get("type") == "loop":
            latest_loop = row
            break
    if latest_loop:
        lb = latest_loop.get("leaderboard_top8", [])
        (OUTDIR / "latest_leaderboard.json").write_text(json.dumps(lb, indent=2), encoding="utf-8")
        write_csv(
            OUTDIR / "latest_leaderboard.csv",
            lb,
            [
                "market_id","market_name","bucket_group_id","bucket_group_title","trade_side",
                "structural_edge","vacuum_score","vacuum_reason","microstructure_score",
                "microstructure_reasons","resolution_score","resolution_reason","total_edge","rank_score"
            ]
        )

        ar = latest_loop.get("allocator_report", {}) or {}
        skip_rows = []
        for k, ids in ar.items():
            if k.startswith("skipped_") and isinstance(ids, list):
                for x in ids:
                    skip_rows.append({"skip_reason": k, "candidate_id": x})
        if skip_rows:
            write_csv(OUTDIR / "allocator_skips.csv", skip_rows, ["skip_reason","candidate_id"])

    # reject reason summary from leaderboard universe isn't fully persisted yet, so summarize from current open/cycle data
    reason_counts = Counter()
    for row in cycle_rows:
        if row.get("type") == "error":
            reason_counts["error"] += 1
        if row.get("type") == "kill":
            reason_counts["kill"] += 1
    reject_summary_rows = [{"reason": k, "count": v} for k, v in sorted(reason_counts.items())]
    write_csv(OUTDIR / "engine_events_summary.csv", reject_summary_rows, ["reason","count"])

    realized = sum(float(r.get("realized_pnl", 0.0) or 0.0) for r in closed_rows)
    open_capital = sum(float(r.get("allocated_capital", 0.0) or 0.0) for r in open_positions)
    summary = {
        "open_trades": len(open_positions),
        "closed_trades": len(closed_rows),
        "open_capital": open_capital,
        "realized_pnl": realized,
        "latest_cycle_count": len(cycle_rows),
    }
    (OUTDIR / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print("desk export complete")
    print("files:")
    for f in sorted(OUTDIR.iterdir()):
        print("-", f)


if __name__ == "__main__":
    main()
