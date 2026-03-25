from polymarket_engine.data_adapters.polymarket_adapter import PolymarketAdapter
import json
from pathlib import Path

adapter = PolymarketAdapter()
OPEN_PATH = Path("logs/trades_open.jsonl")


def _extract_live_price(market: dict):
    if not market:
        return None

    for key in ("current_price", "price", "lastTradePrice", "bestAsk", "bestBid"):
        v = market.get(key)
        if v is None or v == "":
            continue
        try:
            return float(v)
        except (TypeError, ValueError):
            pass

    outcome_prices = market.get("outcomePrices")
    if outcome_prices:
        try:
            if isinstance(outcome_prices, str):
                arr = json.loads(outcome_prices)
            else:
                arr = outcome_prices
            if arr:
                return float(arr[0])
        except Exception:
            pass

    return None


def compute_unrealized_pnl():
    if not OPEN_PATH.exists():
        return 0.0

    total = 0.0

    with OPEN_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            t = json.loads(line)
            market = adapter.get_market_by_id(t["market_id"])
            price = _extract_live_price(market)
            if price is None:
                continue

            entry = float(t["entry_price"])
            size = float(t["filled_size_usd"])
            side = str(t["side"]).upper()

            if side == "LONG":
                pnl = (price - entry) * size
            else:
                pnl = (entry - price) * size

            total += pnl

    return round(total, 6)
