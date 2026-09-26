import argparse
import fcntl
import json
import sqlite3
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import requests


API = "https://gamma-api.polymarket.com/events/keyset"
DEFAULT_DB = Path("analytics/market_measurements.sqlite3")
LOCK_PATH = "/run/signalatlas_universe_scanner.lock"

DEFAULT_PAGE_SIZE = 100
DEFAULT_MAX_PAGES = 1000
SLEEP_MS = 150
MAX_RETRIES = 3

SCHEMA_VERSION = "canonical_universe_v1"


def utcnow():
    return datetime.now(timezone.utc).isoformat()


def acquire_lock():
    fh = open(LOCK_PATH, "w")
    try:
        fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        print("[UNIVERSE_BUSY] another scanner is already running", flush=True)
        raise SystemExit(0)
    return fh


def safe_float(value):
    if value in (None, ""):
        return None
    try:
        return float(value)
    except Exception:
        return None


def bool_int(value):
    if value is True:
        return 1
    if value is False:
        return 0
    return None


def json_list(value):
    if isinstance(value, list):
        return value
    if value in (None, ""):
        return []
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, list) else []
        except Exception:
            return []
    return []


def fetch_page(cursor, page_size):
    params = {
        "limit": page_size,
        "active": "true",
        "closed": "false",
    }

    if cursor:
        params["after_cursor"] = cursor

    last_error = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            r = requests.get(API, params=params, timeout=30)
            r.raise_for_status()
            data = r.json()

            if not isinstance(data, dict):
                raise RuntimeError(
                    f"invalid keyset payload type={type(data).__name__}"
                )

            events = data.get("events")
            next_cursor = data.get("next_cursor")

            if not isinstance(events, list):
                raise RuntimeError(
                    f"invalid events payload type={type(events).__name__}"
                )

            return events, next_cursor

        except Exception as exc:
            last_error = exc
            print(
                f"[UNIVERSE_RETRY] attempt={attempt}/{MAX_RETRIES} "
                f"cursor={cursor!r} error={exc}",
                flush=True,
            )

            if attempt < MAX_RETRIES:
                time.sleep(attempt * 2)

    raise RuntimeError(
        f"event discovery failed after {MAX_RETRIES} attempts: {last_error}"
    )


def lifecycle_state(market):
    active = market.get("active")
    closed = market.get("closed")
    orderbook = market.get("enableOrderBook")

    if closed is True:
        return "CLOSED"

    if active is False:
        return "INACTIVE"

    if active is not True:
        return "UNKNOWN"

    if orderbook is False:
        return "NO_ORDERBOOK"

    return "ACTIVE_CANDIDATE"


def identity_ready(market):
    condition_id = str(market.get("conditionId") or "").strip()
    tokens = json_list(market.get("clobTokenIds"))
    outcomes = json_list(market.get("outcomes"))

    return bool(
        condition_id
        and len(tokens) >= 2
        and len(outcomes) >= 2
    )


def gamma_eligible(market):
    return bool(
        market.get("active") is True
        and market.get("closed") is not True
        and market.get("enableOrderBook") is True
        and identity_ready(market)
    )


def connect_db(path):
    path.parent.mkdir(parents=True, exist_ok=True)

    con = sqlite3.connect(path, timeout=30)
    con.execute("PRAGMA busy_timeout=30000")
    return con


def ensure_schema(con):
    con.executescript(
        """
        CREATE TABLE IF NOT EXISTS universe_discovery_runs (
            run_id TEXT PRIMARY KEY,
            started_at TEXT NOT NULL,
            completed_at TEXT,

            source_endpoint TEXT NOT NULL,
            source_params_json TEXT NOT NULL,

            page_size INTEGER NOT NULL,
            max_pages INTEGER NOT NULL,
            pages_fetched INTEGER NOT NULL DEFAULT 0,

            events_seen INTEGER NOT NULL DEFAULT 0,
            child_markets_seen INTEGER NOT NULL DEFAULT 0,
            unique_markets INTEGER NOT NULL DEFAULT 0,

            live_like_markets INTEGER NOT NULL DEFAULT 0,
            identity_ready_markets INTEGER NOT NULL DEFAULT 0,
            gamma_eligible_markets INTEGER NOT NULL DEFAULT 0,

            completed INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL,
            error_text TEXT,

            schema_version TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS universe_events (
            event_id TEXT PRIMARY KEY,

            title TEXT,
            slug TEXT,

            active INTEGER,
            closed INTEGER,
            enable_order_book INTEGER,

            start_date TEXT,
            end_date TEXT,

            liquidity REAL,
            volume REAL,

            first_seen_at TEXT NOT NULL,
            last_seen_at TEXT NOT NULL,
            last_seen_run_id TEXT NOT NULL,

            schema_version TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS universe_markets (
            market_id TEXT PRIMARY KEY,
            event_id TEXT NOT NULL,

            condition_id TEXT,
            question_id TEXT,

            question TEXT,
            slug TEXT,

            active INTEGER,
            closed INTEGER,
            accepting_orders INTEGER,
            enable_order_book INTEGER,

            restricted INTEGER,
            neg_risk INTEGER,

            start_date TEXT,
            end_date TEXT,

            outcomes_json TEXT NOT NULL,
            clob_token_ids_json TEXT NOT NULL,
            token_count INTEGER NOT NULL,

            liquidity REAL,
            volume REAL,

            lifecycle_state TEXT NOT NULL,
            identity_ready INTEGER NOT NULL,
            gamma_eligible INTEGER NOT NULL,

            clob_state TEXT NOT NULL DEFAULT 'UNVERIFIED',
            tier TEXT NOT NULL DEFAULT 'UNASSIGNED',

            gamma_created_at TEXT,
            gamma_updated_at TEXT,

            first_seen_at TEXT NOT NULL,
            last_seen_at TEXT NOT NULL,
            last_seen_run_id TEXT NOT NULL,

            schema_version TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_universe_markets_event
            ON universe_markets(event_id);

        CREATE INDEX IF NOT EXISTS idx_universe_markets_condition
            ON universe_markets(condition_id);

        CREATE INDEX IF NOT EXISTS idx_universe_markets_eligible
            ON universe_markets(gamma_eligible, clob_state);

        CREATE INDEX IF NOT EXISTS idx_universe_markets_tier
            ON universe_markets(tier);

        CREATE INDEX IF NOT EXISTS idx_universe_markets_last_seen
            ON universe_markets(last_seen_at);
        """
    )
    con.commit()


def upsert_event(con, event, run_id, seen_at):
    event_id = str(event.get("id") or "").strip()
    if not event_id:
        return

    con.execute(
        """
        INSERT INTO universe_events (
            event_id,
            title,
            slug,
            active,
            closed,
            enable_order_book,
            start_date,
            end_date,
            liquidity,
            volume,
            first_seen_at,
            last_seen_at,
            last_seen_run_id,
            schema_version
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)

        ON CONFLICT(event_id) DO UPDATE SET
            title = excluded.title,
            slug = excluded.slug,
            active = excluded.active,
            closed = excluded.closed,
            enable_order_book = excluded.enable_order_book,
            start_date = excluded.start_date,
            end_date = excluded.end_date,
            liquidity = excluded.liquidity,
            volume = excluded.volume,
            last_seen_at = excluded.last_seen_at,
            last_seen_run_id = excluded.last_seen_run_id,
            schema_version = excluded.schema_version
        """,
        (
            event_id,
            event.get("title"),
            event.get("slug"),
            bool_int(event.get("active")),
            bool_int(event.get("closed")),
            bool_int(event.get("enableOrderBook")),
            event.get("startDate"),
            event.get("endDate"),
            safe_float(event.get("liquidity")),
            safe_float(event.get("volume")),
            seen_at,
            seen_at,
            run_id,
            SCHEMA_VERSION,
        ),
    )


def upsert_market(con, event_id, market, run_id, seen_at):
    market_id = str(market.get("id") or "").strip()
    if not market_id:
        return False

    outcomes = json_list(market.get("outcomes"))
    tokens = json_list(market.get("clobTokenIds"))

    ready = int(identity_ready(market))
    eligible = int(gamma_eligible(market))

    con.execute(
        """
        INSERT INTO universe_markets (
            market_id,
            event_id,
            condition_id,
            question_id,
            question,
            slug,
            active,
            closed,
            accepting_orders,
            enable_order_book,
            restricted,
            neg_risk,
            start_date,
            end_date,
            outcomes_json,
            clob_token_ids_json,
            token_count,
            liquidity,
            volume,
            lifecycle_state,
            identity_ready,
            gamma_eligible,
            clob_state,
            tier,
            gamma_created_at,
            gamma_updated_at,
            first_seen_at,
            last_seen_at,
            last_seen_run_id,
            schema_version
        )
        VALUES (
            ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?, ?,
            ?, ?, ?,
            'UNVERIFIED',
            'UNASSIGNED',
            ?, ?, ?, ?, ?, ?
        )

        ON CONFLICT(market_id) DO UPDATE SET
            event_id = excluded.event_id,
            condition_id = excluded.condition_id,
            question_id = excluded.question_id,
            question = excluded.question,
            slug = excluded.slug,
            active = excluded.active,
            closed = excluded.closed,
            accepting_orders = excluded.accepting_orders,
            enable_order_book = excluded.enable_order_book,
            restricted = excluded.restricted,
            neg_risk = excluded.neg_risk,
            start_date = excluded.start_date,
            end_date = excluded.end_date,
            outcomes_json = excluded.outcomes_json,
            clob_token_ids_json = excluded.clob_token_ids_json,
            token_count = excluded.token_count,
            liquidity = excluded.liquidity,
            volume = excluded.volume,
            lifecycle_state = excluded.lifecycle_state,
            identity_ready = excluded.identity_ready,
            gamma_eligible = excluded.gamma_eligible,
            gamma_created_at = excluded.gamma_created_at,
            gamma_updated_at = excluded.gamma_updated_at,
            last_seen_at = excluded.last_seen_at,
            last_seen_run_id = excluded.last_seen_run_id,
            schema_version = excluded.schema_version
        """,
        (
            market_id,
            event_id,
            str(market.get("conditionId") or "") or None,
            str(market.get("questionID") or "") or None,
            market.get("question"),
            market.get("slug"),
            bool_int(market.get("active")),
            bool_int(market.get("closed")),
            bool_int(market.get("acceptingOrders")),
            bool_int(market.get("enableOrderBook")),
            bool_int(market.get("restricted")),
            bool_int(market.get("negRisk")),
            market.get("startDate"),
            market.get("endDate"),
            json.dumps(outcomes, separators=(",", ":")),
            json.dumps(tokens, separators=(",", ":")),
            len(tokens),
            safe_float(
                market.get("liquidityNum")
                if market.get("liquidityNum") is not None
                else market.get("liquidity")
            ),
            safe_float(
                market.get("volumeNum")
                if market.get("volumeNum") is not None
                else market.get("volume")
            ),
            lifecycle_state(market),
            ready,
            eligible,
            market.get("createdAt"),
            market.get("updatedAt"),
            seen_at,
            seen_at,
            run_id,
            SCHEMA_VERSION,
        ),
    )

    return True


def main():
    parser = argparse.ArgumentParser(
        description="SignalAtlas Canonical Universe Index v1"
    )
    parser.add_argument(
        "--db",
        default=str(DEFAULT_DB),
        help="SQLite destination",
    )
    parser.add_argument(
        "--page-size",
        type=int,
        default=DEFAULT_PAGE_SIZE,
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=DEFAULT_MAX_PAGES,
    )
    parser.add_argument(
        "--allow-partial",
        action="store_true",
        help="Do not fail when max-pages is reached before completion",
    )
    args = parser.parse_args()

    if args.page_size < 1 or args.page_size > 500:
        raise SystemExit("page-size must be between 1 and 500")

    if args.max_pages < 1:
        raise SystemExit("max-pages must be >= 1")

    lock_handle = acquire_lock()

    db_path = Path(args.db)
    con = connect_db(db_path)
    ensure_schema(con)

    run_id = str(uuid.uuid4())
    started_at = utcnow()

    source_params = {
        "active": True,
        "closed": False,
        "page_size": args.page_size,
    }

    con.execute(
        """
        INSERT INTO universe_discovery_runs (
            run_id,
            started_at,
            source_endpoint,
            source_params_json,
            page_size,
            max_pages,
            status,
            schema_version
        )
        VALUES (?, ?, ?, ?, ?, ?, 'RUNNING', ?)
        """,
        (
            run_id,
            started_at,
            API,
            json.dumps(source_params, sort_keys=True),
            args.page_size,
            args.max_pages,
            SCHEMA_VERSION,
        ),
    )
    con.commit()

    seen_events = set()
    seen_markets = set()

    pages_fetched = 0
    child_markets_seen = 0
    live_like = 0
    identity_ready_count = 0
    gamma_eligible_count = 0
    completed = False

    cursor = None
    seen_cursors = set()

    try:
        for page in range(args.max_pages):
            events, next_cursor = fetch_page(cursor, args.page_size)
            pages_fetched += 1

            print(
                f"[UNIVERSE_PAGE] page={page + 1} "
                f"events={len(events)} "
                f"unique_events_before={len(seen_events)} "
                f"unique_markets_before={len(seen_markets)}",
                flush=True,
            )

            if not events:
                completed = True
                break

            seen_at = utcnow()

            for event in events:
                event_id = str(event.get("id") or "").strip()
                if not event_id:
                    continue

                if event_id not in seen_events:
                    seen_events.add(event_id)
                    upsert_event(con, event, run_id, seen_at)

                for market in event.get("markets") or []:
                    child_markets_seen += 1

                    market_id = str(market.get("id") or "").strip()
                    if not market_id or market_id in seen_markets:
                        continue

                    seen_markets.add(market_id)

                    if (
                        market.get("active") is True
                        and market.get("closed") is not True
                    ):
                        live_like += 1

                    if identity_ready(market):
                        identity_ready_count += 1

                    if gamma_eligible(market):
                        gamma_eligible_count += 1

                    upsert_market(
                        con,
                        event_id,
                        market,
                        run_id,
                        seen_at,
                    )

            con.commit()

            if not next_cursor:
                completed = True
                break

            if next_cursor == cursor or next_cursor in seen_cursors:
                raise RuntimeError(
                    f"keyset cursor loop detected: {next_cursor!r}"
                )

            seen_cursors.add(next_cursor)
            cursor = next_cursor

            time.sleep(SLEEP_MS / 1000.0)

        status = "COMPLETE" if completed else "PARTIAL_CAP"

        con.execute(
            """
            UPDATE universe_discovery_runs
            SET completed_at = ?,
                pages_fetched = ?,
                events_seen = ?,
                child_markets_seen = ?,
                unique_markets = ?,
                live_like_markets = ?,
                identity_ready_markets = ?,
                gamma_eligible_markets = ?,
                completed = ?,
                status = ?
            WHERE run_id = ?
            """,
            (
                utcnow(),
                pages_fetched,
                len(seen_events),
                child_markets_seen,
                len(seen_markets),
                live_like,
                identity_ready_count,
                gamma_eligible_count,
                int(completed),
                status,
                run_id,
            ),
        )
        con.commit()

        print()
        print("CANONICAL UNIVERSE INDEX v1")
        print("run_id:", run_id)
        print("status:", status)
        print("pages:", pages_fetched)
        print("events:", len(seen_events))
        print("child markets seen:", child_markets_seen)
        print("unique markets:", len(seen_markets))
        print("live-like:", live_like)
        print("identity-ready:", identity_ready_count)
        print("gamma-eligible:", gamma_eligible_count)
        print("db:", db_path)

        if not completed and not args.allow_partial:
            raise RuntimeError(
                f"max-pages={args.max_pages} reached before discovery completed"
            )

    except Exception as exc:
        con.execute(
            """
            UPDATE universe_discovery_runs
            SET completed_at = ?,
                pages_fetched = ?,
                events_seen = ?,
                child_markets_seen = ?,
                unique_markets = ?,
                live_like_markets = ?,
                identity_ready_markets = ?,
                gamma_eligible_markets = ?,
                completed = 0,
                status = 'FAILED',
                error_text = ?
            WHERE run_id = ?
            """,
            (
                utcnow(),
                pages_fetched,
                len(seen_events),
                child_markets_seen,
                len(seen_markets),
                live_like,
                identity_ready_count,
                gamma_eligible_count,
                str(exc),
                run_id,
            ),
        )
        con.commit()
        raise

    finally:
        con.close()
        lock_handle.close()


if __name__ == "__main__":
    main()
