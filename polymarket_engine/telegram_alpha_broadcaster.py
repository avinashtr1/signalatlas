import json
import os
import requests
from pathlib import Path

RANK = Path("analytics/opportunity_ranking.json")
STATE = Path("analytics/pro_alert_state.json")

BOT_TOKEN = os.getenv("TG_BOT_TOKEN", "").strip()
CHANNEL_ID = os.getenv("TG_PRO_CHAT_ID", "").strip()
FORCE_SEND = os.getenv("ALPHA_FORCE_SEND", "0") == "1"

MIN_EDGE_CHANGE = 0.03
MIN_SCORE_CHANGE = 0.05

def load_json(p):
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))

def save_json(p, data):
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")

def send(msg):
    if not BOT_TOKEN or not CHANNEL_ID:
        print("pro telegram env vars missing")
        return False
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    r = requests.post(
        url,
        json={
            "chat_id": CHANNEL_ID,
            "text": msg,
            "disable_web_page_preview": True,
        },
        timeout=15,
    )
    print(r.status_code)
    print(r.text)
    return r.ok


def passes_pro_filter(top):
    mispricing_edge = float(top.get("mispricing_edge", 0.0) or 0.0)
    alpha_score = float(top.get("alpha_score", 0.0) or 0.0)
    opportunity_score = float(top.get("opportunity_score", 0.0) or 0.0)

    if mispricing_edge >= 0.10:
        return True, "strong_mispricing"
    if alpha_score >= 0.20:
        return True, "strong_alpha"
    if opportunity_score >= 0.20:
        return True, "strong_opportunity"

    return False, "below_pro_threshold"


def should_send(prev, curr):
    if not prev:
        return True, "new_market"

    edge_diff = abs(float(curr.get("mispricing_edge", 0.0)) - float(prev.get("mispricing_edge", 0.0)))
    score_diff = abs(float(curr.get("opportunity_score", 0.0)) - float(prev.get("opportunity_score", 0.0)))

    if edge_diff >= MIN_EDGE_CHANGE:
        return True, f"edge_change_{edge_diff:.3f}"

    if score_diff >= MIN_SCORE_CHANGE:
        return True, f"score_change_{score_diff:.3f}"

    return False, "no_material_change"


def is_dominant(rows):
    if not rows:
        return False
    top_edge = float(rows[0].get("mispricing_edge", 0.0) or 0.0)
    if top_edge >= 0.15:
        return True
    if len(rows) < 2:
        return True
    top1 = float(rows[0].get("opportunity_score", 0.0) or 0.0)
    top2 = float(rows[1].get("opportunity_score", 0.0) or 0.0)
    return (top1 - top2) >= 0.05


def main():
    data = load_json(RANK)
    rows = data.get("top_opportunities", [])
    state = load_json(STATE)
    markets = state.get("markets", {})

    if not rows:
        print("no ranked opportunities")
        return

    sent_any = False

    if not is_dominant(rows):
        print('skip: no dominant signal')
        return

    for top in rows[:1]:
        market = top["market_name"]

        passes, filter_reason = passes_pro_filter(top)
        if not passes:
            print(f"skip {market}: {filter_reason}")
            continue

        prev = markets.get(market)
        if FORCE_SEND:
            ok, reason = True, "force_send"
        else:
            ok, reason = should_send(prev, top)

        if not ok:
            print(f"skip {market}: {reason}")
            continue

        msg = f"""🚨 SIGNALATLAS PRO ALERT

Market
{market}

Opportunity Score
{round(top['opportunity_score'], 3)}

Alpha Score
{round(top['alpha_score'], 3)}

Mispricing Edge
{round(top['mispricing_edge'], 3)}

Liquidity Collapse
{round(top['collapse_score'], 3)}

Reason
{reason}

—
Recent Performance: strong signal accuracy tracking live
"""

        if send(msg):
            markets[market] = {
                "opportunity_score": float(top.get("opportunity_score", 0.0) or 0.0),
                "alpha_score": float(top.get("alpha_score", 0.0) or 0.0),
                "mispricing_edge": float(top.get("mispricing_edge", 0.0) or 0.0),
                "collapse_score": float(top.get("collapse_score", 0.0) or 0.0),
            }
            sent_any = True

    state["markets"] = markets
    save_json(STATE, state)

    if not sent_any:
        print("no new pro alerts sent")

if __name__ == "__main__":
    main()
