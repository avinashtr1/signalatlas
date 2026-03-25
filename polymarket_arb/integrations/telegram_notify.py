"""
Telegram notifications for Polymarket scanner
With persistent deduplication
"""

import os
import subprocess
import json
import hashlib
from datetime import datetime, timedelta
from pathlib import Path


# Telegram config
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "8507543198:AAHnnGtvEmuc6WRwLd0LYMWxY_6TuZQ0wB8")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "919721442")

# Fee model
FEE_PER_LEG = 0.01

# Deduplication state
DEDUPE_FILE = Path("/root/.openclaw/workspace/polymarket_arb/storage/dedupe_state.json")
_last_alert_state = {}


def _load_state():
    """Load state from file"""
    global _last_alert_state
    try:
        if DEDUPE_FILE.exists():
            with open(DEDUPE_FILE, "r") as f:
                _last_alert_state = json.load(f)
    except:
        _last_alert_state = {}


def _save_state():
    """Save state to file"""
    global _last_alert_state
    try:
        DEDUPE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(DEDUPE_FILE, "w") as f:
            json.dump(_last_alert_state, f)
    except:
        pass


# Load on import
_load_state()


def generate_arb_signature(candidate: dict, decision: str) -> str:
    """Generate unique signature for arb"""
    val = candidate.get("validation", {})
    legs = val.get("legs", [])
    
    leg_data = []
    for leg in legs:
        mid = leg.get("market_id", "")
        outcome = leg.get("outcome", "")
        price = leg.get("price", 0)
        leg_data.append(f"{mid}|{outcome}|{price:.3f}")
    
    cluster = candidate.get("cluster", "unknown")
    leg_str = "_".join(sorted(leg_data))
    hash_input = f"{cluster}_{leg_str}_{decision}"
    return hashlib.md5(hash_input.encode()).hexdigest()[:8]


def is_new_or_changed(candidate: dict, decision: str) -> bool:
    """Check if this arb is new or meaningfully changed"""
    global _last_alert_state
    
    signature = generate_arb_signature(candidate, decision)
    val = candidate.get("validation", {})
    net_edge = val.get("net_edge_after_fees", 0)
    
    current_state = {
        "signature": signature,
        "net_edge": net_edge,
        "decision": decision
    }
    
    if signature in _last_alert_state:
        last = _last_alert_state[signature]
        if last["decision"] == decision:
            if abs(current_state["net_edge"] - last["net_edge"]) < 0.005:
                return False
    
    _last_alert_state[signature] = current_state
    _save_state()
    return True


def send_telegram_message(message: str):
    """Send message via Telegram Bot API (MOCKED for now)"""
    # MOCKED: Just print to console
    print(f"--- [MOCK TELEGRAM] ---\n{message}\n-----------------------")
    return True


def calculate_time_to_resolution(end_date_str: str):
    """Calculate time to resolution"""
    try:
        end_date = datetime.strptime(end_date_str.replace("Z", ""), "%Y-%m-%d")
        delta = end_date - datetime.now()
        if delta.days < 0: return "Expired", "Past"
        elif delta.days == 0: return "Today", "<1d"
        elif delta.days < 30: return f"{delta.days} days", f"{delta.days}d"
        elif delta.days < 365: return f"{delta.days//30} months", f"{delta.days//30}mo"
        else: return f"{delta.days//365} years", f"{delta.days//365}y"
    except: return "Unknown", "TBD"


def assess_risks(candidate: dict, end_date_str=None):
    """Assess risks"""
    risks = []
    val = candidate.get("validation", {})
    legs = val.get("legs", [])
    
    if end_date_str:
        time_str, _ = calculate_time_to_resolution(end_date_str)
        if "year" in time_str.lower(): risks.append("Long duration")
        if "month" in time_str.lower() and int(time_str.split()[0] if time_str.split()[0].isdigit() else 0) > 6: risks.append(f"Duration {time_str}")
    
    for leg in legs:
        if leg.get("price", 0) > 0.80:
            risks.append(f"Low liq: {leg.get('market_id', '')[:10]}")
            break
    
    if len(legs) > 3: risks.append(f"Many legs ({len(legs)})")
    if val.get("net_edge_after_fees", 0) < 0.03: risks.append("Thin edge")
    
    cluster = candidate.get("cluster", "").lower()
    if "election" in cluster: risks.append("Event risk")
    if "crypto" in cluster: risks.append("Volatility risk")
    
    return risks if risks else ["None"]


def calculate_confidence_score(candidate: dict, risks: list) -> int:
    """Calculate confidence 1-10"""
    score = 10
    val = candidate.get("validation", {})
    for risk in risks:
        if "Long" in risk or "Low" in risk or "Thin" in risk: score -= 2
        elif "Many" in risk: score -= 1
    if val.get("arb_type") == "MUST_HAPPEN": score += 1
    return max(1, min(10, score))


def notify_arb_decision(candidate: dict, decision: str, reasons: list, end_date_str=None):
    """Send full arb alert"""
    if not is_new_or_changed(candidate, decision):
        print(f"[SKIP] Same arb, no change")
        return
    
    val = candidate.get("validation", {})
    cluster = candidate.get("cluster", "unknown").upper()
    signature = generate_arb_signature(candidate, decision)
    
    risks = assess_risks(candidate, end_date_str)
    time_label, _ = calculate_time_to_resolution(end_date_str or "2026-12-31")
    confidence = calculate_confidence_score(candidate, risks)
    conf_emoji = "🟢" if confidence >= 7 else "🟡" if confidence >= 5 else "🔴"
    
    # Format legs
    leg_lines = []
    for leg in val.get("legs", []):
        mid = leg.get("market_id", "?")[:15]
        outcome = leg.get("outcome", "?")
        price = leg.get("price", 0)
        liq_flag = "⚠️" if price > 0.80 else "✓"
        leg_lines.append(f"   {liq_flag} {mid}\n     {outcome}: {price:.2f}")
    
    emoji = "✅" if decision == "ACCEPT" else "❌"
    
    lines = [
        f"{emoji} ARB: {decision}",
        f"ID: {signature} | Score: {conf_emoji} {confidence}/10",
        f"Cluster: {cluster} | Type: {val.get('arb_type', 'N/A')} | Res: {time_label}",
        "",
        f"📊 Edge: {val.get('edge', 0):.1%} → Net: {val.get('net_edge_after_fees', 0):.1%} (~1%/leg)",
        "",
        f"📋 Legs ({len(val.get('legs', []))}):",
        "\n".join(leg_lines) if leg_lines else "   (none)",
        "",
        f"⚠️ Risks: {', '.join(risks)}",
        f"💡 {', '.join(reasons[:3])}"
    ]
    
    send_telegram_message("\n".join(lines))
    print("\n".join(lines))


def notify_scanner_alive(cycle: int, found: int):
    send_telegram_message(f"💓 Heartbeat\nCycle #{cycle}\nArbs: {found}\nStatus: Running")


def notify_error(error: str):
    send_telegram_message(f"❌ Error\n{error}")
