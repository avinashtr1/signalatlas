import json
from pathlib import Path
from datetime import datetime, timezone

ALPHA = Path("analytics/alpha_fusion_signals.json")
RANK = Path("analytics/opportunity_ranking.json")
TIERS = Path("analytics/tiers.json")
OUT = Path("analytics/intelligence_feed_v2.txt")

def load_json(p):
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))

def risk_label(alpha, collapse):
    if alpha >= 0.45 and collapse <= 0.12:
        return "LOW"
    if alpha >= 0.25 and collapse <= 0.25:
        return "MEDIUM"
    return "HIGH"

def conf_label(c):
    if c >= 0.85:
        return "HIGH"
    if c >= 0.65:
        return "MEDIUM"
    return "LOW"

def urg_label(u):
    if u >= 0.60:
        return "EXTREME"
    if u >= 0.45:
        return "HIGH"
    if u >= 0.30:
        return "MEDIUM"
    return "LOW"

def entry_band(mid_price, spread, fallback_score):
    if mid_price is not None and spread is not None:
        lo = max(0.0, mid_price - spread/2)
        hi = min(1.0, mid_price + spread/2)
        return round(lo, 3), round(hi, 3)

    center = fallback_score
    lo = max(0.0, center - 0.02)
    hi = min(1.0, center + 0.02)
    return round(lo, 3), round(hi, 3)

def main():
    alpha = load_json(ALPHA).get("signals", [])
    rank = load_json(RANK).get("top_opportunities", [])
    tiers = load_json(TIERS).get("tiers", [])

    alpha_map = {r.get("market_name"): r for r in alpha if r.get("market_name")}
    tier_map = {r.get("market_name"): r for r in tiers if r.get("market_name")}

    lines = []
    lines.append("🚨 SIGNALATLAS PRO FEED V2")
    lines.append("")
    lines.append(f"Generated: {datetime.now(timezone.utc).isoformat()}")
    lines.append("")

    if not rank:
        lines.append("No ranked opportunities.")
    else:
        for i, r in enumerate(rank[:5], 1):
            name = r.get("market_name")
            a = alpha_map.get(name, {})
            t = tier_map.get(name, {})

            alpha_score = float(a.get("alpha_score", r.get("alpha_score", 0.0)) or 0.0)
            mispricing = float(a.get("mispricing_edge", r.get("mispricing_edge", 0.0)) or 0.0)
            collapse = float(a.get("collapse_score", r.get("collapse_score", 0.0)) or 0.0)
            confidence = float(a.get("confidence_score", 0.0) or 0.0)
            urgency = float(a.get("execution_urgency", 0.0) or 0.0)
            opp = float(r.get("opportunity_score", 0.0) or 0.0)

            mid_price = a.get("mid_price")
            spread = a.get("spread")
            lo, hi = entry_band(mid_price, spread, float(a.get("radar_score", 0.5) or 0.5))

            tier = t.get("tier", "D")
            quality = t.get("quality", "weak")

            lines.append(f"{i}. {name}")
            lines.append(f"   Tier: {tier} ({quality})")
            lines.append(f"   Opportunity: {opp:.3f}")
            lines.append(f"   Alpha: {alpha_score:.3f}")
            lines.append(f"   Mispricing: {mispricing:.3f}")
            lines.append(f"   Collapse: {collapse:.3f}")
            lines.append(f"   Confidence: {conf_label(confidence)} ({confidence:.3f})")
            lines.append(f"   Urgency: {urg_label(urgency)} ({urgency:.3f})")
            lines.append(f"   Risk: {risk_label(alpha_score, collapse)}")
            lines.append(f"   Entry Band: {lo} - {hi}")
            lines.append("")

    OUT.write_text("\n".join(lines), encoding="utf-8")
    print("FEED V2 FORMATTER BUILT")
    print("file:", OUT)

if __name__ == "__main__":
    main()
