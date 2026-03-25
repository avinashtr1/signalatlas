import json
import hashlib
import os
from pathlib import Path
from datetime import datetime, timezone

from polymarket_engine.utils.telegram_notifier import TelegramNotifier

RADAR_PATH = Path("analytics/radar_live.json")
QUALITY_PATH = Path("analytics/alpha_quality_scores.json")
ALLOCATOR_PATH = Path("analytics/portfolio_allocator.json")

STATE_DIR = Path("analytics/.state")
SENT_ALERTS_PATH = STATE_DIR / "radar_alerts_sent.json"

OUT_JSON = Path("analytics/radar_alerts.json")
OUT_TXT = Path("analytics/radar_alerts.txt")

def load_json(path, default=None):
    if default is None:
        default = {}
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))

def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")

def short_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]

def build_quality_map():
    data = load_json(QUALITY_PATH, {})
    out = {}
    for r in data.get("scores", []):
        name = r.get("market_name")
        if name:
            out[name] = r
    return out

def build_alloc_map():
    data = load_json(ALLOCATOR_PATH, {})
    out = {}
    for r in data.get("allocations", []):
        name = r.get("market_name")
        if name:
            out[name] = r
    return out

def format_alert(item, q=None, a=None):
    q = q or {}
    a = a or {}

    market = item.get("market_name", "Unknown market")
    market_id = item.get("market_id")
    slug = item.get("slug")
    if slug:
        link = f"https://polymarket.com/event/{slug}"
    elif market_id:
        link = f"https://polymarket.com/market/{market_id}"
    else:
        link = ""
    side = item.get("side", "N/A")
    edge = float(item.get("expected_net_edge_pct", 0.0) or 0.0)
    gross_edge = float(item.get("total_edge", 0.0) or 0.0) * 100.0
    rank = item.get("rank", "-")
    grade = q.get("grade", "N/A")
    qscore = float(q.get("quality_score", 0.0) or 0.0)
    vacuum = float(item.get("vacuum_score", 0.0) or 0.0)
    micro = float(item.get("microstructure_score", 0.0) or 0.0)
    capital = float(a.get("suggested_capital", 0.0) or 0.0)
    alloc_tier = a.get("allocation_tier", "N/A")

    emoji = "🔴" if str(side).upper() in {"SHORT", "SELL", "NO"} else "🟢"

    lines = [
        "🚨 SIGNALATLAS PREMIUM ALERT",
        "",
        f"{emoji} {market}",
        "",
        f"Signal: {side}",
        f"Rank: #{rank} | Grade: {grade}",
        f"Radar Score: {float(item.get('adaptive_radar_score', 0.0) or 0.0):.3f} | Tier: {item.get('radar_tier', 'D')}",
        f"Net Edge: {edge:.2f}%",
        f"Gross Edge: {gross_edge:.2f}%",
        f"Quality Score: {qscore:.3f}",
        f"Vacuum: {vacuum:.2f} | Micro: {micro:.2f}",
        f"Suggested Capital: ${capital:.2f}",
        f"Allocation Tier: {alloc_tier}",
        "",
        "Trade Now:",
        link,
        "",
        "Powered by SignalAtlas",
    ]
    return "\n".join(lines)

def main():
    send_tg = os.getenv("RADAR_SEND_TG", "0") == "1"
    force_send = os.getenv("RADAR_FORCE_SEND", "0") == "1"

    radar = load_json(RADAR_PATH, {})
    deploy_now = radar.get("deploy_now", [])

    quality_map = build_quality_map()
    alloc_map = build_alloc_map()

    sent_state = load_json(SENT_ALERTS_PATH, {"sent_ids": []})
    sent_ids = set(sent_state.get("sent_ids", []))

    alerts = []
    new_sent_ids = set(sent_ids)

    for item in deploy_now:
        market = item.get("market_name", "")
        side = item.get("side", "")
        rank = str(item.get("rank", ""))
        edge = f"{float(item.get('expected_net_edge_pct', 0.0) or 0.0):.4f}"
        alert_id = short_hash(f"{market}|{side}|{rank}|{edge}")

        q = quality_map.get(market, {})
        a = alloc_map.get(market, {})
        text = format_alert(item, q, a)

        alerts.append({
            "alert_id": alert_id,
            "market_name": market,
            "text": text,
            "is_new": force_send or alert_id not in sent_ids,
        })

    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "count": len(alerts),
        "new_count": sum(1 for a in alerts if a["is_new"]),
        "alerts": [
            {
                "alert_id": a["alert_id"],
                "market_name": a["market_name"],
                "is_new": a["is_new"],
            }
            for a in alerts
        ],
    }
    save_json(OUT_JSON, payload)

    preview_lines = ["SIGNALATLAS RADAR ALERT ENGINE", ""]
    if not alerts:
        preview_lines.append("No deploy-now alerts.")
    else:
        for i, a in enumerate(alerts, start=1):
            preview_lines.append(f"{i}. {a['market_name']} | new={a['is_new']}")
    OUT_TXT.write_text("\n".join(preview_lines), encoding="utf-8")

    print("\n".join(preview_lines))
    print("")

    if not send_tg:
        print("RADAR_SEND_TG=0: dry run, not sending")
        return

    tg = TelegramNotifier()
    sent_any = 0
    for a in alerts:
        if not a["is_new"]:
            continue
        ok = tg.send(a["text"])
        print(f"sent {a['market_name']}: {ok}")
        if ok:
            sent_any += 1
            new_sent_ids.add(a["alert_id"])

    save_json(SENT_ALERTS_PATH, {"sent_ids": sorted(new_sent_ids)})
    print("")
    print(f"alerts_sent: {sent_any}")
    print("files created:")
    print("analytics/radar_alerts.json")
    print("analytics/radar_alerts.txt")

if __name__ == "__main__":
    main()
