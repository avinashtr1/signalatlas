import json
import sys
from pathlib import Path

BASE = Path("analytics")

def read_json(name):
    path = BASE / name
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))

def cmd_ops_summary():
    exec_ = read_json("executive_brief.json")
    radar = read_json("opportunity_radar.json").get("radar", {})
    quality = read_json("alpha_quality_scores.json").get("scores", [])
    allocator = read_json("portfolio_allocator.json")

    out = {
        "status": exec_.get("system_status", "UNKNOWN"),
        "signals_detected": exec_.get("signals_detected", 0),
        "signals_executed": exec_.get("signals_executed", 0),
        "signals_resolved": exec_.get("signals_resolved", 0),
        "deploy_now_count": exec_.get("deploy_now_count", 0),
        "shock_count": exec_.get("shock_count", 0),
        "drift_count": exec_.get("drift_count", 0),
        "collapse_count": exec_.get("collapse_count", 0),
        "allocated_capital": exec_.get("total_allocated_capital", 0),
        "top_opportunity": exec_.get("top_opportunity", {}),
        "deploy_now": radar.get("deploy_now", [])[:5],
        "top_quality": quality[:5],
        "allocator": {
            "reference_equity": allocator.get("reference_equity", 0),
            "total_allocated_capital": allocator.get("total_allocated_capital", 0),
            "total_allocated_pct": allocator.get("total_allocated_pct", 0),
        },
        "recommendations": exec_.get("recommendations", []),
    }
    print(json.dumps(out, indent=2))

def cmd_ops_brief():
    exec_ = read_json("executive_brief.json")
    radar = read_json("opportunity_radar.json").get("radar", {})
    quality = read_json("alpha_quality_scores.json").get("scores", [])

    lines = []
    lines.append("SIGNALATLAS OPS BRIEF")
    lines.append("")
    lines.append(f"Status: {exec_.get('system_status', 'UNKNOWN')}")
    lines.append(
        f"Signals: detected={exec_.get('signals_detected', 0)} "
        f"executed={exec_.get('signals_executed', 0)} "
        f"resolved={exec_.get('signals_resolved', 0)}"
    )
    lines.append(
        f"Deploy-Now: {exec_.get('deploy_now_count', 0)} | "
        f"Drift: {exec_.get('drift_count', 0)} | "
        f"Shocks: {exec_.get('shock_count', 0)} | "
        f"Collapse: {exec_.get('collapse_count', 0)}"
    )
    lines.append(f"Allocated Capital: {float(exec_.get('total_allocated_capital', 0)):.2f}")
    lines.append("")

    top = exec_.get("top_opportunity") or {}
    if top.get("market_name"):
        lines.append("TOP OPPORTUNITY")
        lines.append(
            f"{top['market_name']} | side={top.get('side')} | "
            f"edge={float(top.get('total_edge', 0))*100:.2f}% | "
            f"net={float(top.get('expected_net_edge_pct', 0)):.2f}%"
        )
        lines.append("")

    deploy = radar.get("deploy_now", [])
    if deploy:
        lines.append("DEPLOY NOW")
        for i, r in enumerate(deploy[:5], start=1):
            lines.append(f"{i}. {r.get('market_name')} | edge={float(r.get('total_edge', 0))*100:.2f}%")
        lines.append("")

    if quality:
        lines.append("TOP QUALITY")
        for i, r in enumerate(quality[:5], start=1):
            lines.append(f"{i}. {r.get('market_name')} | grade={r.get('grade')} | score={float(r.get('quality_score', 0)):.3f}")
        lines.append("")

    recs = exec_.get("recommendations", [])
    if recs:
        lines.append("RECOMMENDATIONS")
        for i, r in enumerate(recs, start=1):
            lines.append(f"{i}. {r}")

    print("\n".join(lines))

def cmd_deploy_now():
    radar = read_json("opportunity_radar.json").get("radar", {})
    rows = radar.get("deploy_now", [])
    if not rows:
        print("No deploy-now opportunities.")
        return
    for i, r in enumerate(rows[:10], start=1):
        print(
            f"{i}. {r.get('market_name')} | "
            f"side={r.get('side')} | "
            f"edge={float(r.get('total_edge', 0))*100:.2f}% | "
            f"net={float(r.get('expected_net_edge_pct', 0)):.2f}%"
        )

def cmd_top_quality():
    rows = read_json("alpha_quality_scores.json").get("scores", [])
    if not rows:
        print("No quality scores.")
        return
    for i, r in enumerate(rows[:10], start=1):
        print(
            f"{i}. {r.get('market_name')} | "
            f"grade={r.get('grade')} | "
            f"score={float(r.get('quality_score', 0)):.3f} | "
            f"edge={float(r.get('total_edge', 0))*100:.2f}%"
        )

def cmd_help():
    print("Usage:")
    print("  python3 -m polymarket_engine.agent_queries ops-summary")
    print("  python3 -m polymarket_engine.agent_queries ops-brief")
    print("  python3 -m polymarket_engine.agent_queries deploy-now")
    print("  python3 -m polymarket_engine.agent_queries top-quality")

def main():
    if len(sys.argv) < 2:
        cmd_help()
        return

    cmd = sys.argv[1].strip().lower()

    if cmd == "ops-summary":
        cmd_ops_summary()
    elif cmd == "ops-brief":
        cmd_ops_brief()
    elif cmd == "deploy-now":
        cmd_deploy_now()
    elif cmd == "top-quality":
        cmd_top_quality()
    else:
        cmd_help()

if __name__ == "__main__":
    main()
