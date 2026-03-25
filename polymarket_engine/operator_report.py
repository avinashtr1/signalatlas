import json
from pathlib import Path
from datetime import datetime, timedelta

CLOSED = Path("logs/trades_closed.jsonl")
OPEN = Path("logs/trades_open.jsonl")
LEDGER = Path("analytics/opportunity_ledger.jsonl")

from polymarket_engine.utils.channel_sender import send

def load_jsonl(p):
    if not p.exists():
        return []
    return [json.loads(x) for x in p.read_text().splitlines() if x.strip()]

def main():
    now = datetime.utcnow()
    one_hour_ago = now - timedelta(hours=1)

    closed = load_jsonl(CLOSED)
    recent = [x for x in closed if datetime.fromisoformat(x["ts"].replace("Z","+00:00")) >= one_hour_ago]

    pnls = [float(x.get("realized_pnl",0) or 0) for x in recent]
    wins = [x for x in pnls if x > 0]
    losses = [x for x in pnls if x < 0]

    open_trades = load_jsonl(OPEN)

    last_reason = recent[-1]["close_reason"] if recent else "n/a"

    msg = f"""📊 SIGNALATLAS HOURLY

Trades (1h): {len(recent)}
PnL (1h): {round(sum(pnls),2)}

Win Rate: {round(len(wins)/len(pnls)*100,1) if pnls else 0}%

Open Positions: {len(open_trades)}

Last Close: {last_reason}

Recent PnLs:
{[round(x,2) for x in pnls[-5:]]}
"""

    send("operator", msg)

if __name__ == "__main__":
    main()
