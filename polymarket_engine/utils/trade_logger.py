import json
from datetime import datetime, timezone
from pathlib import Path


class TradeLogger:
    def __init__(self, open_path="logs/trades_open.jsonl", closed_path="logs/trades_closed.jsonl"):
        self.open_path = Path(open_path)
        self.closed_path = Path(closed_path)

        self.open_path.parent.mkdir(parents=True, exist_ok=True)
        self.closed_path.parent.mkdir(parents=True, exist_ok=True)

    def _write_jsonl(self, path: Path, payload: dict):
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")

    def log_open(self, position: dict, candidate=None, analysis=None):
        payload = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "event": "OPEN",
            "trade_id": position.get("trade_id"),
            "market_id": position.get("market_id"),
            "bucket_group_id": position.get("bucket_group_id"),
            "bucket_group_title": position.get("bucket_group_title"),
            "side": position.get("side"),
            "entry_price": position.get("entry_price"),
            "filled_size_usd": position.get("filled_size_usd"),
            "allocated_capital": position.get("allocated_capital"),
            "fill_ratio": position.get("fill_ratio"),
            "extra_slippage": position.get("extra_slippage"),
            "strategy_type": position.get("strategy_type"),
            "execution_mode": position.get("execution_mode"),
        }

        if candidate is not None:
            payload.update({
                "market_name": getattr(candidate.market_state, "name", None),
                "event_group": getattr(candidate.market_state, "event_group", None),
            })

        if analysis is not None:
            payload.update({
                "trade_side": analysis.get("trade_side"),
                "structural_edge": analysis.get("structural_edge"),
                "total_edge": analysis.get("total_edge"),
                "microstructure_score": analysis.get("microstructure_score"),
                "microstructure_reasons": analysis.get("microstructure_reasons"),
                "expected_net_edge_pct": analysis.get("expected_net_edge_pct"),
                "expected_fill_probability": analysis.get("expected_fill_probability"),
                "vacuum_score": analysis.get("vacuum_score"),
                "vacuum_signal": analysis.get("vacuum_signal"),
            })

        self._write_jsonl(self.open_path, payload)

    def log_close(self, position: dict):
        payload = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "event": "CLOSE",
            "trade_id": position.get("trade_id"),
            "market_id": position.get("market_id"),
            "bucket_group_id": position.get("bucket_group_id"),
            "bucket_group_title": position.get("bucket_group_title"),
            "side": position.get("side"),
            "entry_price": position.get("entry_price"),
            "filled_size_usd": position.get("filled_size_usd"),
            "allocated_capital": position.get("allocated_capital"),
            "realized_pnl": position.get("realized_pnl"),
            "strategy_type": position.get("strategy_type"),
            "execution_mode": position.get("execution_mode"),
        }
        self._write_jsonl(self.closed_path, payload)
