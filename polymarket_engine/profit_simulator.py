import json
from pathlib import Path
from datetime import datetime, timezone

OUT = Path("analytics/signal_outcomes.json")
PROFIT = Path("analytics/profit_simulation.json")

ENTRY_SIZE = 100  # dollars per signal

def load_json(p):
    if not p.exists():
        return {}
    return json.loads(p.read_text())

def save_json(p,data):
    p.write_text(json.dumps(data,indent=2))

def main():

    data = load_json(OUT)
    rows = data.get("rows",[])

    capital = 0
    wins = 0
    losses = 0
    trades = 0

    equity_curve = []

    for r in rows:

        status = r.get("evaluation_status")
        move = r.get("evaluation_move")

        if status not in ["validated","failed"]:
            continue

        trades += 1

        pnl = ENTRY_SIZE * move
        capital += pnl

        if pnl > 0:
            wins += 1
        else:
            losses += 1

        equity_curve.append(capital)

    winrate = (wins/trades) if trades else 0

    result = {
        "timestamp":datetime.now(timezone.utc).isoformat(),
        "signals_total":len(rows),
        "trades":trades,
        "wins":wins,
        "losses":losses,
        "winrate":round(winrate,3),
        "capital_pnl":round(capital,2),
        "equity_curve":equity_curve[-200:]
    }

    save_json(PROFIT,result)

    print("PROFIT SIM COMPLETE")
    print(result)

if __name__ == "__main__":
    main()
