import os
import json
import fcntl
import sqlite3
from pathlib import Path
from datetime import datetime, timezone

from polymarket_engine.data_adapters.polymarket_adapter import PolymarketAdapter


OUT = Path("analytics/market_raw.json")
DB = Path("analytics/market_measurements.sqlite3")
LOCK = Path("/run/signalatlas_market_raw_collector.lock")

EVENT_LIMIT = 100
BUCKET_MINUTES = 15


def floor_bucket(dt):
    minute = (dt.minute // BUCKET_MINUTES) * BUCKET_MINUTES
    return dt.replace(
        minute=minute,
        second=0,
        microsecond=0,
    ).isoformat()


def token_map(adapter, raw_market, quote):
    outcomes = adapter._parse_json_list(raw_market.get("outcomes"))

    tokens = quote.get("clob_token_ids") or adapter._parse_json_list(
        raw_market.get("clobTokenIds")
    )

    yes_token_id = None
    no_token_id = None

    for i, outcome in enumerate(outcomes):
        if i >= len(tokens):
            break

        label = str(outcome).strip().lower()

        if label == "yes":
            yes_token_id = str(tokens[i])
        elif label == "no":
            no_token_id = str(tokens[i])

    return outcomes, tokens, yes_token_id, no_token_id


def init_db(conn):
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA busy_timeout=5000")

    conn.execute("""
        CREATE TABLE IF NOT EXISTS snapshots (
            market_id TEXT NOT NULL,
            event_id TEXT,
            market_name TEXT,
            event_title TEXT,

            observed_at TEXT NOT NULL,
            observation_bucket TEXT NOT NULL,
            source_updated_at TEXT,
            source TEXT NOT NULL,

            reference_price REAL,
            best_bid REAL,
            best_ask REAL,
            mid_price REAL,
            spread REAL,
            quote_state TEXT NOT NULL,

            two_sided INTEGER NOT NULL,
            tradable_top_of_book INTEGER NOT NULL,

            active INTEGER NOT NULL,
            closed INTEGER NOT NULL,
            archived INTEGER NOT NULL,
            accepting_orders INTEGER NOT NULL,

            volume_total_usd REAL,
            liquidity_usd REAL,

            yes_token_id TEXT,
            no_token_id TEXT,

            structural_group_type TEXT,
            neg_risk INTEGER NOT NULL,
            neg_risk_augmented INTEGER NOT NULL,
            neg_risk_market_id TEXT,
            bucket_group_id TEXT,

            raw_resolution_time TEXT,
            resolution_time_valid INTEGER NOT NULL,

            schema_version TEXT NOT NULL,

            PRIMARY KEY (market_id, observation_bucket)
        )
    """)

    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_snapshots_market_time
        ON snapshots (market_id, observed_at)
    """)

    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_snapshots_observed
        ON snapshots (observed_at)
    """)

    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_snapshots_group
        ON snapshots (structural_group_type, observation_bucket)
    """)

    conn.execute("PRAGMA user_version=2")


def append_measurements(rows, observation_bucket):
    sql = """
        INSERT OR IGNORE INTO snapshots (
            market_id,
            event_id,
            market_name,
            event_title,

            observed_at,
            observation_bucket,
            source_updated_at,
            source,

            reference_price,
            best_bid,
            best_ask,
            mid_price,
            spread,
            quote_state,

            two_sided,
            tradable_top_of_book,

            active,
            closed,
            archived,
            accepting_orders,

            volume_total_usd,
            liquidity_usd,

            yes_token_id,
            no_token_id,

            structural_group_type,
            neg_risk,
            neg_risk_augmented,
            neg_risk_market_id,
            bucket_group_id,

            raw_resolution_time,
            resolution_time_valid,

            schema_version
        )
        VALUES (
            :market_id,
            :event_id,
            :market_name,
            :event_title,

            :observed_at,
            :observation_bucket,
            :source_updated_at,
            :source,

            :reference_price,
            :best_bid,
            :best_ask,
            :mid_price,
            :spread,
            :quote_state,

            :two_sided,
            :tradable_top_of_book,

            :active,
            :closed,
            :archived,
            :accepting_orders,

            :volume_total_usd,
            :liquidity_usd,

            :yes_token_id,
            :no_token_id,

            :structural_group_type,
            :neg_risk,
            :neg_risk_augmented,
            :neg_risk_market_id,
            :bucket_group_id,

            :raw_resolution_time,
            :resolution_time_valid,

            :schema_version
        )
    """

    records = []

    for r in rows:
        records.append({
            "market_id": str(r.get("market_id")),
            "event_id": str(r.get("event_id"))
            if r.get("event_id") is not None else None,

            "market_name": r.get("market_name"),
            "event_title": r.get("event_title"),

            "observed_at": r.get("observed_at"),
            "observation_bucket": observation_bucket,
            "source_updated_at": r.get("source_updated_at"),
            "source": "POLYMARKET_GAMMA_TOP_OF_BOOK",

            "reference_price": r.get("reference_price"),
            "best_bid": r.get("best_bid"),
            "best_ask": r.get("best_ask"),
            "mid_price": r.get("mid_price"),
            "spread": r.get("spread"),
            "quote_state": r.get("quote_state") or "UNKNOWN",

            "two_sided": int(bool(r.get("two_sided"))),
            "tradable_top_of_book": int(
                bool(r.get("tradable_top_of_book"))
            ),

            "active": int(bool(r.get("active"))),
            "closed": int(bool(r.get("closed"))),
            "archived": int(bool(r.get("archived"))),
            "accepting_orders": int(
                bool(r.get("accepting_orders"))
            ),

            "volume_total_usd": r.get("volume_total_usd"),
            "liquidity_usd": r.get("liquidity_usd"),

            "yes_token_id": str(r.get("yes_token_id"))
            if r.get("yes_token_id") else None,

            "no_token_id": str(r.get("no_token_id"))
            if r.get("no_token_id") else None,

            "structural_group_type": r.get(
                "structural_group_type"
            ),

            "neg_risk": int(bool(r.get("neg_risk"))),

            "neg_risk_augmented": int(
                bool(r.get("neg_risk_augmented"))
            ),

            "neg_risk_market_id": r.get(
                "neg_risk_market_id"
            ),

            "bucket_group_id": r.get("bucket_group_id"),

            "raw_resolution_time": r.get(
                "raw_resolution_time"
            ),

            "resolution_time_valid": int(
                bool(r.get("resolution_time_valid"))
            ),

            "schema_version": "canonical_snapshot_v1",
        })

    tradable = sum(
        1 for r in rows
        if r.get("tradable_top_of_book") is True
    )

    with sqlite3.connect(DB) as conn:
        init_db(conn)

        before = conn.total_changes
        conn.executemany(sql, records)
        inserted = conn.total_changes - before

        total = conn.execute(
            "SELECT COUNT(*) FROM snapshots"
        ).fetchone()[0]

        conn.commit()

    return len(records), tradable, inserted, total


def main():
    LOCK.parent.mkdir(parents=True, exist_ok=True)

    with LOCK.open("w") as lock_fp:
        try:
            fcntl.flock(
                lock_fp,
                fcntl.LOCK_EX | fcntl.LOCK_NB
            )
        except BlockingIOError:
            raise SystemExit(
                "MARKET_RAW_COLLECTOR_ALREADY_RUNNING"
            )

        adapter = PolymarketAdapter()

        collected_dt = datetime.now(timezone.utc)
        collected_at = collected_dt.isoformat()
        observation_bucket = floor_bucket(collected_dt)

        events = adapter._fetch_active_events(
            limit=EVENT_LIMIT
        )

        if not events:
            raise SystemExit("NO_ACTIVE_EVENTS_RETURNED")

        rows = []

        for event in events:
            event_id = str(event.get("id"))

            event_title = (
                event.get("title")
                or event.get("slug")
                or f"event_{event_id}"
            )

            raw_by_id = {}

            for raw in event.get("markets") or []:
                try:
                    market_id = str(
                        adapter._extract_market_id(raw)
                    )
                    raw_by_id[market_id] = raw
                except Exception:
                    continue

            normalized = (
                adapter._normalize_bucket_event_markets(event)
            )

            for market in normalized:
                market_id = str(market.get("market_id"))
                raw = raw_by_id.get(market_id, {})

                quote = (
                    market.get("liquidity_snapshot") or {}
                )

                (
                    outcomes,
                    token_ids,
                    yes_token_id,
                    no_token_id,
                ) = token_map(adapter, raw, quote)

                active = raw.get("active") is True
                closed = raw.get("closed") is True
                archived = raw.get("archived") is True
                accepting_orders = (
                    raw.get("acceptingOrders") is True
                )

                tradable_top_of_book = bool(
                    active
                    and not closed
                    and not archived
                    and accepting_orders
                    and quote.get("two_sided") is True
                )

                volume = quote.get("volume_total_usd")
                liquidity = quote.get("liquidity_usd")

                rows.append({
                    "schema_version":
                        "canonical_snapshot_v1",

                    "market_id": market_id,
                    "market_name": market.get("name"),
                    "event_id": event_id,
                    "event_title": event_title,

                    "observed_at":
                        quote.get("observed_at")
                        or collected_at,
                    "source_updated_at":
                        quote.get("source_updated_at"),
                    "source": "POLYMARKET_GAMMA",

                    "reference_price":
                        market.get("current_price"),
                    "best_bid": quote.get("best_bid"),
                    "best_ask": quote.get("best_ask"),
                    "mid_price": quote.get("mid_price"),
                    "spread": quote.get("spread"),
                    "quote_state":
                        quote.get("quote_state"),
                    "two_sided":
                        quote.get("two_sided"),
                    "tradable_top_of_book":
                        tradable_top_of_book,

                    "active": active,
                    "closed": closed,
                    "archived": archived,
                    "accepting_orders":
                        accepting_orders,

                    "volume_total_usd": volume,
                    "liquidity_usd": liquidity,

                    "outcomes": outcomes,
                    "clob_token_ids": token_ids,
                    "yes_token_id": yes_token_id,
                    "no_token_id": no_token_id,

                    "structural_group_type":
                        market.get(
                            "structural_group_type",
                            "STANDALONE",
                        ),
                    "structural_group_verified":
                        market.get(
                            "structural_group_verified",
                            False,
                        ),
                    "structural_group_analysis_eligible":
                        market.get(
                            "structural_group_analysis_eligible",
                            False,
                        ),
                    "neg_risk":
                        market.get("neg_risk", False),
                    "neg_risk_augmented":
                        market.get(
                            "neg_risk_augmented",
                            False,
                        ),
                    "neg_risk_market_id":
                        market.get("neg_risk_market_id"),
                    "bucket_group_id":
                        market.get("bucket_group_id"),
                    "bucket_group_title":
                        market.get("bucket_group_title"),
                    "group_item_title":
                        market.get("group_item_title"),

                    "raw_resolution_time":
                        market.get(
                            "raw_resolution_time"
                        ),
                    "resolution_time_valid":
                        market.get(
                            "resolution_time_valid",
                            False,
                        ),

                    # Compatibility aliases
                    "current_price":
                        market.get("current_price"),
                    "volume": volume,
                    "liquidity": liquidity,
                })

        if not rows:
            raise SystemExit("NO_MARKETS_NORMALIZED")

        observed, tradable, inserted, history_total = (
            append_measurements(
                rows,
                observation_bucket,
            )
        )

        payload = {
            "schema_version":
                "canonical_snapshot_collection_v1",
            "timestamp": collected_at,
            "observation_bucket": observation_bucket,
            "count": len(rows),
            "source":
                "POLYMARKET_GAMMA_ACTIVE_EVENTS",
            "source_scope": {
                "event_limit": EVENT_LIMIT,
                "events_returned": len(events),
                "complete_universe": False,
            },
            "measurement_history": {
                "bucket_minutes": BUCKET_MINUTES,
                "observed_this_run": observed,
                "tradable_two_sided_this_run": tradable,
                "inserted_this_run": inserted,
                "total_snapshots": history_total,
                "database":
                    "analytics/market_measurements.sqlite3",
            },
            "rows": rows,
        }

        OUT.parent.mkdir(parents=True, exist_ok=True)

        tmp = OUT.with_name(
            f"{OUT.name}.tmp.{os.getpid()}"
        )

        tmp.write_text(
            json.dumps(payload, indent=2),
            encoding="utf-8",
        )

        os.replace(tmp, OUT)

        print("CANONICAL_MARKET_RAW_BUILT")
        print("events =", len(events))
        print("markets =", len(rows))
        print("observation_bucket =", observation_bucket)
        print("markets_observed =", observed)
        print("tradable_two_sided =", tradable)
        print("history_inserted =", inserted)
        print("history_total =", history_total)
        print("latest =", OUT)
        print("history =", DB)


if __name__ == "__main__":
    main()
