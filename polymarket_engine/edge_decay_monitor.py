import json
from pathlib import Path
from datetime import datetime, timezone

from polymarket_engine.data_adapters.polymarket_adapter import PolymarketAdapter
from polymarket_engine.models.trigger_event import TriggerEvent
from polymarket_engine.triggers.market_mapper import MarketMapper
from polymarket_engine.config.market_filters import MarketFilterConfig
from polymarket_engine.brain.evaluate import BrainEvaluator
from polymarket_engine.brain.inventory import Inventory
from polymarket_engine.brain.gates import Gates

OPEN_LOG = Path("logs/trades_open.jsonl")

EDGE_DECAY_THRESHOLD = 0.60

adapter = PolymarketAdapter()
filter_config = MarketFilterConfig()
mapper = MarketMapper(filter_config)
mapper.polymarket_adapter = adapter
brain = BrainEvaluator(filter_config, Gates(), Inventory(100000.0))


def load_open_trades():
    rows = []
    if not OPEN_LOG.exists():
        return rows
    with OPEN_LOG.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def detect_edge_decay():
    trades = load_open_trades()
    exits = []

    trigger = TriggerEvent("market_scan", "system", "ALL", datetime.now(timezone.utc), {})
    live_candidates = mapper.map_trigger_to_candidates(trigger)

    by_market_id = {}
    for c in live_candidates:
        by_market_id[str(c.market_state.market_id)] = c

    for t in trades:
        market_id = str(t.get("market_id"))
        live_candidate = by_market_id.get(market_id)
        if not live_candidate:
            continue

        result = brain.evaluate_candidate(live_candidate)
        analysis = result.get("analysis", {}) or {}

        entry_edge = float(t.get("total_edge", 0.0) or 0.0)
        current_edge = float(analysis.get("total_edge", 0.0) or 0.0)

        if entry_edge <= 0:
            continue

        try:
            opened_ts = datetime.fromisoformat(str(t.get("ts")).replace("Z", "+00:00"))
            age_minutes = (datetime.now(timezone.utc) - opened_ts).total_seconds() / 60.0
        except Exception:
            age_minutes = 0.0

        entry_price = float(t.get("entry_price", 0.0) or 0.0)
        filled_size = float(t.get("filled_size_usd", 0.0) or 0.0)
        side = str(t.get("side", "LONG")).upper()

        try:
            live_price = float(getattr(live_candidate.market_state, "current_price", 0.0) or 0.0)
        except Exception:
            live_price = 0.0

        if side == "SHORT":
            realized = filled_size * (entry_price - live_price)
        else:
            realized = filled_size * (live_price - entry_price)

        decay = 1.0 - (current_edge / entry_edge)

        if age_minutes >= 90 and realized <= 0.05 and decay >= EDGE_DECAY_THRESHOLD:
            exits.append({
                "trade_id": t.get("trade_id"),
                "market_id": market_id,
                "market_name": t.get("market_name"),
                "entry_edge": round(entry_edge, 4),
                "current_edge": round(current_edge, 4),
                "decay": round(decay, 3),
                "age_minutes": round(age_minutes, 1),
                "realized": round(realized, 4),
            })

    return exits
