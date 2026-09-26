
from pathlib import Path
import json

PERF_PATH = Path("analytics/performance_analytics.json")

def load_perf():
    if PERF_PATH.exists():
        return json.loads(PERF_PATH.read_text())
    return {}
import json
from pathlib import Path
from datetime import datetime, timezone

REPUTATION_PATH = Path("analytics/signal_reputation_full.json")
LEADERBOARD_PATH = Path("analytics/alpha_leaderboard.json")
RADAR_PATH = Path("analytics/opportunity_radar.json")
SHOCK_PATH = Path("analytics/probability_shocks.json")
DRIFT_PATH = Path("analytics/probability_drift_report.json")
COLLAPSE_PATH = Path("analytics/liquidity_collapse_report.json")
ALLOCATOR_PATH = Path("analytics/portfolio_allocator.json")

OUT_JSON = Path("analytics/executive_brief.json")
OUT_TXT = Path("analytics/executive_brief.txt")

def load_json(path):
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))

def top_recommendation(leaderboard):
    rows = leaderboard.get("leaderboard", [])
    if not rows:
        return None
    return rows[0]

def build_recommendations(rep, radar, shocks, drifts, collapses):
    recs = []

    detected = int(rep.get("signals_detected", 0) or 0)
    executed = int(rep.get("signals_executed", 0) or 0)
    resolved = int(rep.get("signals_resolved", 0) or 0)

    deploy_now = radar.get("radar", {}).get("deploy_now", [])
    shock_count = int(shocks.get("shock_count", 0) or 0)
    drift_count = int(drifts.get("count", 0) or 0)
    collapse_count = int(collapses.get("count", 0) or 0)

    if detected == 0:
        recs.append("No signals detected yet — keep engine running and collect data.")
    elif resolved == 0:
        recs.append("No signals resolved yet — focus on data accumulation and avoid over-interpreting early PnL.")

    if deploy_now:
        recs.append(f"{len(deploy_now)} deploy-now opportunities available — prioritize monitoring highest-ranked names.")

    if shock_count > 0:
        recs.append(f"{shock_count} probability shock events detected — review for short-term dislocation opportunities.")

    if drift_count > 0:
        recs.append(f"{drift_count} probability drift markets detected — review for trend or overreaction behavior.")

    if collapse_count > 0:
        recs.append(f"{collapse_count} liquidity collapse signals detected — investigate for vacuum-driven edge.")

    if detected > 0 and executed == detected:
        recs.append("Execution rate is 100% — later we should improve filtering so only highest-quality signals are deployed.")

    if not recs:
        recs.append("System healthy. Continue running pipeline and collecting signal history.")

    return recs

def main():
    perf = load_perf()
    rep = load_json(REPUTATION_PATH)
    leaderboard = load_json(LEADERBOARD_PATH)
    radar = load_json(RADAR_PATH)
    shocks = load_json(SHOCK_PATH)
    drifts = load_json(DRIFT_PATH)
    collapses = load_json(COLLAPSE_PATH)
    allocator = load_json(ALLOCATOR_PATH)

    top = top_recommendation(leaderboard)
    recommendations = build_recommendations(rep, radar, shocks, drifts, collapses)

    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "system_status": "HEALTHY",
        "signals_detected": rep.get("signals_detected", 0),
        "signals_executed": rep.get("signals_executed", 0),
        "signals_resolved": rep.get("signals_resolved", 0),
        "win_rate": rep.get("win_rate", 0),
        "realized_pnl": rep.get("realized_pnl", 0),
        "deploy_now_count": len(radar.get("radar", {}).get("deploy_now", [])),
        "shock_count": shocks.get("shock_count", 0),
        "drift_count": drifts.get("count", 0),
        "collapse_count": collapses.get("count", 0),
        "total_allocated_capital": allocator.get("total_allocated_capital", 0),
        "top_opportunity": top,
        "recommendations": recommendations,
    }

    OUT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    lines = []
    lines.append("SIGNALATLAS EXECUTIVE BRIEF")
    lines.append("")
    lines.append(f"System Status: {payload['system_status']}")
    lines.append(f"Signals Detected: {payload['signals_detected']}")
    lines.append(f"Signals Executed: {payload['signals_executed']}")
    lines.append(f"Signals Resolved: {payload['signals_resolved']}")
    lines.append(f"Win Rate: {float(payload['win_rate'])*100:.2f}%")
    lines.append(f"Realized PnL: {float(payload['realized_pnl']):.4f}")
    lines.append(f"Deploy-Now Opportunities: {payload['deploy_now_count']}")
    lines.append(f"Probability Shocks: {payload['shock_count']}")
    lines.append(f"Probability Drift: {payload['drift_count']}")
    lines.append(f"Liquidity Collapse: {payload['collapse_count']}")
    lines.append(f"Allocated Capital: {float(payload['total_allocated_capital']):.2f}")
    lines.append("")

    if top:
        lines.append("TOP OPPORTUNITY")
        lines.append(f"Market: {top.get('market_name')}")
        lines.append(f"Side: {top.get('side')}")
        lines.append(f"Edge: {float(top.get('total_edge', 0))*100:.2f}%")
        lines.append(f"Net Edge: {float(top.get('expected_net_edge_pct', 0)):.2f}%")
        lines.append("")

    lines.append("RECOMMENDATIONS")
    for i, r in enumerate(recommendations, start=1):
        lines.append(f"{i}. {r}")

    text = "\n".join(lines)
    OUT_TXT.write_text(text, encoding="utf-8")

    print(text)
    print("")
    print("files created:")
    print("analytics/executive_brief.json")
    print("analytics/executive_brief.txt")

if __name__ == "__main__":
    main()
