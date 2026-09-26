import json
import re
import csv
from pathlib import Path
from datetime import datetime

POLY_FILE = "analytics/polymarket_snapshot.json"
KALSHI_FILE = "analytics/kalshi_manual_snapshot.json"
LOG_FILE = "analytics/arb_log.csv"

POLY_FEE = 0.02
KALSHI_FEE = 0.02
SLIPPAGE = 0.01

EXECUTION_SLIP = 0.02
FAIL_PROB = 0.15

TEST_SIZES = [10, 50, 100]

def load(path):
    if not Path(path).exists():
        return []
    return json.loads(Path(path).read_text())

def normalize(name):
    n = name.lower()

    # politics
    if "senate" in n and "2026" in n:
        if "democrat" in n:
            return "senate_dem_2026"
        if "republican" in n:
            return "senate_rep_2026"

    # btc
    if "bitcoin" in n or "btc" in n:
        if "100k" in n or "100,000" in n:
            if "above" in n or "over" in n:
                return "btc_above_100k"
            if "below" in n or "under" in n:
                return "btc_below_100k"

    # recession
    if "recession" in n:
        if "no" in n:
            return "recession_no"
        return "recession_yes"

    # trump
    if "trump" in n and "2028" in n:
        if "win" in n:
            return "trump_win_2028"
        if "lose" in n:
            return "trump_lose_2028"

    # fed
    if "fed" in n and "2025" in n:
        if "cut" in n:
            return "fed_cut_2025"
        if "not" in n:
            return "fed_no_cut_2025"

    return None

def build_maps(rows, is_kalshi=False):
    out = {}
    for r in rows:
        key = normalize(r.get("market_name",""))
        if not key:
            continue

        if is_kalshi:
            out[key] = {
                "name": r["market_name"],
                "bid": float(r.get("yes_bid", 0)),
                "ask": float(r.get("yes_ask", 0)),
                "size": float(r.get("size", 0)),
            }
        else:
            price = float(r.get("yes_price", 0))
            out[key] = {
                "name": r["market_name"],
                "bid": price * 0.99,
                "ask": price * 1.01,
                "size": 1000,
            }
    return out

def log_row(row):
    file_exists = Path(LOG_FILE).exists()
    with open(LOG_FILE, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=row.keys())
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)

def run():
    poly_rows = load(POLY_FILE)
    kalshi_rows = load(KALSHI_FILE)

    print(f"Loaded {len(poly_rows)} poly | {len(kalshi_rows)} kalshi")

    poly = build_maps(poly_rows)
    kalshi = build_maps(kalshi_rows, True)

    now = datetime.utcnow().isoformat()

    for k in set(poly.keys()) & set(kalshi.keys()):
        poly_bid = poly[k]["bid"]
        kalshi_ask = kalshi[k]["ask"]

        base_edge = abs(poly_bid - kalshi[k]["bid"])
        if base_edge < 0.01:
            continue

        slipped = base_edge - EXECUTION_SLIP
        fail_loss = -0.10

        expected_edge = (
            (1 - FAIL_PROB) * slipped +
            FAIL_PROB * fail_loss
        )

        net_edge = expected_edge - (POLY_FEE + KALSHI_FEE + SLIPPAGE)

        print(f"\nMATCH: {k}\nPOLY: {poly[k]["name"]}\nKALSHI: {kalshi[k]["name"]}")
        print("POLY BID:", poly[k]["bid"], "KALSHI ASK:", kalshi[k]["ask"], "BASE EDGE:", round(base_edge,4))

        for size in TEST_SIZES:
            eff_size = min(size, kalshi[k]["size"])
            pnl = net_edge * eff_size

            log_row({
                "timestamp": now,
                "market": k,
                "poly_bid": round(poly_bid,4),
                "kalshi_ask": round(kalshi_ask,4),
                "net_edge": round(net_edge,4),
                "size": eff_size,
                "expected_pnl": round(pnl,4)
            })

if __name__ == "__main__":
    run()
