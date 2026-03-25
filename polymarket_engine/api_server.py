import json
from pathlib import Path
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse, JSONResponse

app = FastAPI(title="SignalAtlas API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE = Path("analytics")

FILES = {
    "regime": BASE / "market_regime_live.json",
    "opportunities": BASE / "opportunity_ranking.json",
    "tiers": BASE / "tiers.json",
    "alpha": BASE / "alpha_fusion_signals.json",
    "report_txt": BASE / "intelligence_report.txt",
    "mispricing": BASE / "mispricing_signals.json",
    "repricing": BASE / "probability_repricing.json",
    "leadlag": BASE / "cross_market_lead_lag.json",
    "shocks": BASE / "market_shocks.json",
    "feed_v2": BASE / "intelligence_feed_v2.txt",
    "signal_memory": BASE / "signal_memory.json",
    "edge_decay": BASE / "edge_decay.json",
    "outcomes": BASE / "signal_outcomes.json",
    "profit": BASE / "profit_simulation.json",
    "market_graph": BASE / "market_graph.json",
    "cross_market": BASE / "cross_market_signals.json",
    "prob_velocity": BASE / "probability_velocity.json",
    "universe": BASE / "market_universe.json",
    "universe_clean": BASE / "market_universe_clean.json",
    "clusters": BASE / "narrative_clusters.json",
    "mispricing_live": BASE / "mispricing_signals.json",
}

def load_json(path: Path):
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Missing file: {path.name}")
    return json.loads(path.read_text(encoding="utf-8"))

def load_text(path: Path):
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Missing file: {path.name}")
    return path.read_text(encoding="utf-8")

@app.get("/api/health")
def health():
    return {"ok": True, "service": "SignalAtlas API"}

@app.get("/api/regime")
def regime():
    return load_json(FILES["regime"])

@app.get("/api/opportunities")
def opportunities():
    return load_json(FILES["opportunities"])

@app.get("/api/tiers")
def tiers():
    return load_json(FILES["tiers"])

@app.get("/api/alpha")
def alpha():
    return load_json(FILES["alpha"])

@app.get("/api/mispricing")
def mispricing():
    return load_json(FILES["mispricing"])

@app.get("/api/repricing")
def repricing():
    return load_json(FILES["repricing"])

@app.get("/api/leadlag")
def leadlag():
    return load_json(FILES["leadlag"])

@app.get("/api/shocks")
def shocks():
    return load_json(FILES["shocks"])

@app.get("/api/signal-memory")
def signal_memory():
    return load_json(FILES["signal_memory"])

@app.get("/api/edge-decay")
def edge_decay():
    return load_json(FILES["edge_decay"])

@app.get("/api/report", response_class=PlainTextResponse)
def report():
    return load_text(FILES["report_txt"])

@app.get("/api/feed-v2", response_class=PlainTextResponse)
def feed_v2():
    return load_text(FILES["feed_v2"])
@app.get("/api/signal-stats")
def signal_stats():
    rows = load_json(FILES["signal_memory"]).get("rows", [])

    validated = 0
    failed = 0
    watching = 0

    for r in rows:
        outcome = r.get("outcome_pnl")

        if outcome is None:
            watching += 1
        elif outcome > 0:
            validated += 1
        elif outcome < 0:
            failed += 1

    total = validated + failed

    success_rate = 0
    if total > 0:
        success_rate = round(validated / total, 3)

    return {
        "validated": validated,
        "failed": failed,
        "watching": watching,
        "success_rate": success_rate
    }


@app.get("/api/outcomes")
def outcomes():
    return load_json(FILES["outcomes"])


@app.get("/api/profit")
def profit():
    return load_json(FILES["profit"])


@app.get("/api/market-graph")
def market_graph():
    return load_json(FILES["market_graph"])


@app.get("/api/cross-market")
def cross_market():
    return load_json(FILES["cross_market"])


@app.get("/api/universe")
def universe():
    return load_json(FILES["universe"])


@app.get("/api/probability-velocity")
def prob_velocity():
    return load_json(FILES["prob_velocity"])


@app.get("/api/universe-clean")
def universe_clean():
    return load_json(FILES["universe_clean"])

@app.get("/api/clusters")
def clusters():
    return load_json(FILES["clusters"])


@app.get("/api/mispricing-live")
def mispricing_live():
    return load_json(FILES["mispricing_live"])


def _read_jsonl(path, limit=50):
    p = Path(path)
    if not p.exists():
        return []
    rows = []
    with p.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except Exception:
                pass
    return rows[-limit:]

@app.get("/api/execution-history")
def execution_history():
    open_trades = _read_jsonl("logs/trades_open.jsonl", 50)
    closed_trades = _read_jsonl("logs/trades_closed.jsonl", 50)

    open_map = {}
    for t in _read_jsonl("logs/trades_open.jsonl", 500):
        trade_id = t.get("trade_id")
        if trade_id:
            open_map[str(trade_id)] = t

    enriched_closed = []
    for c in closed_trades:
        trade_id = str(c.get("trade_id"))
        o = open_map.get(trade_id, {})

        expected_edge_pct = float(o.get("expected_net_edge_pct", 0) or 0)
        allocated_capital = float(o.get("allocated_capital", c.get("allocated_capital", 0)) or 0)
        realized_pnl = float(c.get("realized_pnl", 0) or 0)

        expected_edge = allocated_capital * (expected_edge_pct / 100.0)
        realized_edge = realized_pnl
        edge_capture = (realized_edge / expected_edge) if expected_edge not in (0, None) else None
        edge_lost = (expected_edge - realized_edge) if expected_edge not in (0, None) else None
        efficiency_pct = (edge_capture * 100.0) if edge_capture is not None else None

        entry_ts = o.get("ts") or o.get("entry_timestamp")
        close_ts = c.get("ts")
        holding_minutes = None
        try:
            if entry_ts and close_ts:
                e = datetime.fromisoformat(str(entry_ts).replace("Z", "+00:00"))
                z = datetime.fromisoformat(str(close_ts).replace("Z", "+00:00"))
                holding_minutes = max(0.0, (z - e).total_seconds() / 60.0)
        except Exception:
            holding_minutes = None

        x = dict(c)
        x["expected_edge_pct"] = round(expected_edge_pct, 4)
        x["expected_edge"] = round(expected_edge, 6)
        x["realized_edge"] = round(realized_edge, 6)
        x["edge_capture"] = round(edge_capture, 6) if edge_capture is not None else None
        x["edge_lost"] = round(edge_lost, 6) if edge_lost is not None else None
        x["efficiency_pct"] = round(efficiency_pct, 4) if efficiency_pct is not None else None
        x["holding_minutes"] = round(holding_minutes, 2) if holding_minutes is not None else None
        enriched_closed.append(x)

    return {
        "open_trades": open_trades,
        "closed_trades": enriched_closed,
    }
@app.get("/api/portfolio-summary")
def portfolio_summary():

    open_trades = _read_jsonl("logs/trades_open.jsonl", 500)
    closed_trades = _read_jsonl("logs/trades_closed.jsonl", 500)

    closed_ids = {x["trade_id"] for x in closed_trades}

    active = [t for t in open_trades if t["trade_id"] not in closed_ids]

    realized_pnl = sum(float(x.get("realized_pnl", 0)) for x in closed_trades)

    capital_locked = sum(float(x.get("allocated_capital", 0)) for x in active)

    return {
        "open_positions": len(active),
        "closed_positions": len(closed_trades),
        "realized_pnl": round(realized_pnl, 2),
        "capital_locked": round(capital_locked, 2),
        "latest_close": closed_trades[-1] if closed_trades else None
    }

@app.get("/api/open-trades")
def open_trades():

    open_trades = _read_jsonl("logs/trades_open.jsonl", 500)
    closed_trades = _read_jsonl("logs/trades_closed.jsonl", 500)

    closed_ids = {x["trade_id"] for x in closed_trades}

    active = [t for t in open_trades if t["trade_id"] not in closed_ids]

    return active


@app.get("/api/execution_truth")
def get_execution_truth():
    from pathlib import Path
    import json

    p = Path("analytics/execution_truth.json")
    if not p.exists():
        return {"error": "execution_truth not found"}

    return json.loads(p.read_text(encoding="utf-8"))
