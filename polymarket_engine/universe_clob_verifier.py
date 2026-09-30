#!/usr/bin/env python3
import argparse
import fcntl
import json
import sqlite3
import sys
import time
import uuid
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT))

from py_clob_client.client import ClobClient
from py_clob_client.clob_types import BookParams

from polymarket_engine.orderbook_collector import (
    HOST,
    BATCH_SIZE,
    book_token,
    summarize_book,
)

SCHEMA_VERSION = "canonical_clob_verification_v1"
DEFAULT_DB = Path("analytics/market_measurements.sqlite3")
LOCK_PATH = Path("/run/signalatlas_universe_verifier.lock")

CADENCE_MINUTES = {
    "HOT": 30,
    "WARM": 120,
    "COLD": 720,
}
TRANSPORT_RETRY_MINUTES = 10
MAX_RETRIES = 3
UPDATE_COMMIT_CHUNK = 250


def utcnow():
    return datetime.now(timezone.utc)


def iso(dt):
    return dt.astimezone(timezone.utc).isoformat()


def parse_dt(value):
    if not value:
        return None
    try:
        s = str(value).strip()
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def safe_json_list(value):
    if value in (None, ""):
        return []
    if isinstance(value, list):
        return value
    try:
        x = json.loads(value)
        return x if isinstance(x, list) else []
    except Exception:
        return []


def add_column_if_missing(con, table, name, definition):
    cols = {
        row[1]
        for row in con.execute(f"PRAGMA table_info({table})")
    }
    if name not in cols:
        con.execute(
            f"ALTER TABLE {table} ADD COLUMN {name} {definition}"
        )


def ensure_schema(con):
    tables = {
        r[0]
        for r in con.execute("""
            SELECT name
            FROM sqlite_master
            WHERE type='table'
        """)
    }

    if "universe_markets" not in tables:
        raise RuntimeError("universe_markets table missing")

    add_column_if_missing(
        con, "universe_markets",
        "clob_last_verified_at", "TEXT"
    )
    add_column_if_missing(
        con, "universe_markets",
        "clob_next_check_at", "TEXT"
    )
    add_column_if_missing(
        con, "universe_markets",
        "clob_good_streak", "INTEGER NOT NULL DEFAULT 0"
    )
    add_column_if_missing(
        con, "universe_markets",
        "clob_bad_streak", "INTEGER NOT NULL DEFAULT 0"
    )
    add_column_if_missing(
        con, "universe_markets",
        "clob_transport_error_streak", "INTEGER NOT NULL DEFAULT 0"
    )
    add_column_if_missing(
        con, "universe_markets",
        "clob_last_error", "TEXT"
    )
    add_column_if_missing(
        con, "universe_markets",
        "clob_last_latency_ms", "REAL"
    )
    add_column_if_missing(
        con, "universe_markets",
        "clob_last_returned_tokens", "INTEGER"
    )
    add_column_if_missing(
        con, "universe_markets",
        "clob_verification_schema", "TEXT"
    )
    add_column_if_missing(
        con, "universe_markets",
        "tier_updated_at", "TEXT"
    )

    con.executescript("""
        CREATE TABLE IF NOT EXISTS universe_clob_verification_runs (
            run_id TEXT PRIMARY KEY,
            started_at TEXT NOT NULL,
            completed_at TEXT,

            db_path TEXT NOT NULL,
            requested_limit INTEGER NOT NULL,

            markets_selected INTEGER NOT NULL DEFAULT 0,
            tokens_requested INTEGER NOT NULL DEFAULT 0,

            batches_total INTEGER NOT NULL DEFAULT 0,
            batches_ok INTEGER NOT NULL DEFAULT 0,
            batches_failed INTEGER NOT NULL DEFAULT 0,

            state_counts_json TEXT,
            tier_counts_json TEXT,

            wall_seconds REAL,
            status TEXT NOT NULL,
            error_text TEXT,

            schema_version TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_universe_markets_clob_due
        ON universe_markets (
            gamma_eligible,
            clob_next_check_at,
            tier,
            clob_state
        );

        CREATE INDEX IF NOT EXISTS idx_universe_markets_clob_state
        ON universe_markets (clob_state);

        CREATE INDEX IF NOT EXISTS idx_universe_markets_tier_due
        ON universe_markets (tier, clob_next_check_at);
    """)

    add_column_if_missing(
        con, "universe_clob_verification_runs",
        "markets_processed", "INTEGER NOT NULL DEFAULT 0"
    )
    add_column_if_missing(
        con, "universe_clob_verification_runs",
        "markets_committed", "INTEGER NOT NULL DEFAULT 0"
    )

    con.commit()


def reconcile_abandoned_runs(con, now_dt):
    """
    Close stale RUNNING rows left by a prior interrupted verifier process.

    Because the verifier lock is already held when this runs, any pre-existing
    RUNNING row is stale and can be marked ABANDONED safely.
    """
    rows = con.execute("""
        SELECT run_id
        FROM universe_clob_verification_runs
        WHERE status = 'RUNNING'
    """).fetchall()

    if not rows:
        return 0

    con.execute("""
        UPDATE universe_clob_verification_runs
        SET completed_at = ?,
            status = 'ABANDONED',
            error_text = COALESCE(
                error_text,
                'previous verifier process ended before run finalization'
            )
        WHERE status = 'RUNNING'
    """, (iso(now_dt),))
    con.commit()

    return len(rows)


def acquire_lock():
    fh = LOCK_PATH.open("w")
    try:
        fcntl.flock(
            fh.fileno(),
            fcntl.LOCK_EX | fcntl.LOCK_NB,
        )
    except BlockingIOError:
        raise SystemExit(
            "[UNIVERSE_VERIFIER_BUSY] another verifier is running"
        )
    return fh


def due_count(con, now_iso):
    return con.execute("""
        SELECT COUNT(*)
        FROM universe_markets
        WHERE gamma_eligible = 1
          AND (
                clob_next_check_at IS NULL
                OR clob_next_check_at <= ?
              )
    """, (now_iso,)).fetchone()[0]


def select_due(con, now_iso, limit):
    # Production steady-state scheduler.
    #
    # Capacity reservations are derived dynamically from the
    # current eligible tier population and canonical cadence.
    #
    # Each tier receives guaranteed capacity when overdue. Any unused
    # reservation spills over to the globally oldest remaining due work.
    # This prevents HOT backlog from starving slower tiers while keeping
    # the scheduler work-conserving.
    # Derive scheduler capacity from the current eligible tier
    # population and each tier's canonical verification cadence.
    #
    # demand(tier) = eligible markets / cadence minutes
    #
    # This preserves the cadence-derived service ratio as universe
    # composition changes instead of freezing today's population mix.
    tier_counts = {
        row[0]: int(row[1])
        for row in con.execute("""
            SELECT tier, COUNT(*)
            FROM universe_markets
            WHERE gamma_eligible = 1
              AND tier IN ('HOT', 'WARM', 'COLD')
            GROUP BY tier
        """)
    }

    demands = {
        tier: (
            tier_counts.get(tier, 0)
            / CADENCE_MINUTES[tier]
        )
        for tier in ("HOT", "WARM", "COLD")
    }

    total_demand = sum(demands.values())

    if total_demand > 0:
        shares = tuple(
            (
                tier,
                demands[tier] / total_demand,
            )
            for tier in ("HOT", "WARM", "COLD")
        )
    else:
        shares = ()

    selected = []
    selected_ids = set()

    for tier, share in shares:
        quota = int(limit * share)

        if quota <= 0:
            continue

        rows = con.execute("""
            SELECT
                market_id,
                event_id,
                clob_token_ids_json,
                end_date,
                clob_state,
                tier,
                clob_good_streak,
                clob_bad_streak,
                clob_transport_error_streak,
                clob_next_check_at
            FROM universe_markets
            WHERE gamma_eligible = 1
              AND tier = ?
              AND (
                    clob_next_check_at IS NULL
                    OR clob_next_check_at <= ?
                  )
            ORDER BY
                CASE
                    WHEN clob_next_check_at IS NULL THEN 0
                    ELSE 1
                END,
                clob_next_check_at ASC,
                market_id ASC
            LIMIT ?
        """, (
            tier,
            now_iso,
            quota,
        )).fetchall()

        selected.extend(rows)
        selected_ids.update(
            str(row["market_id"])
            for row in rows
        )

    remaining = limit - len(selected)

    if remaining > 0:
        if selected_ids:
            ids = sorted(selected_ids)
            placeholders = ",".join("?" for _ in ids)

            sql = f"""
                SELECT
                    market_id,
                    event_id,
                    clob_token_ids_json,
                    end_date,
                    clob_state,
                    tier,
                    clob_good_streak,
                    clob_bad_streak,
                    clob_transport_error_streak,
                    clob_next_check_at
                FROM universe_markets
                WHERE gamma_eligible = 1
                  AND (
                        clob_next_check_at IS NULL
                        OR clob_next_check_at <= ?
                      )
                  AND market_id NOT IN ({placeholders})
                ORDER BY
                    CASE
                        WHEN clob_next_check_at IS NULL THEN 0
                        ELSE 1
                    END,
                    clob_next_check_at ASC,
                    market_id ASC
                LIMIT ?
            """

            params = [
                now_iso,
                *ids,
                remaining,
            ]

            rows = con.execute(
                sql,
                params,
            ).fetchall()

        else:
            rows = con.execute("""
                SELECT
                    market_id,
                    event_id,
                    clob_token_ids_json,
                    end_date,
                    clob_state,
                    tier,
                    clob_good_streak,
                    clob_bad_streak,
                    clob_transport_error_streak,
                    clob_next_check_at
                FROM universe_markets
                WHERE gamma_eligible = 1
                  AND (
                        clob_next_check_at IS NULL
                        OR clob_next_check_at <= ?
                      )
                ORDER BY
                    CASE
                        WHEN clob_next_check_at IS NULL THEN 0
                        ELSE 1
                    END,
                    clob_next_check_at ASC,
                    market_id ASC
                LIMIT ?
            """, (
                now_iso,
                remaining,
            )).fetchall()

        selected.extend(rows)

    return selected


def fetch_batch(client, token_ids):
    last_error = None

    for attempt in range(1, MAX_RETRIES + 1):
        t0 = time.perf_counter()

        try:
            books = client.get_order_books(
                [BookParams(token_id=t) for t in token_ids]
            )
            latency_ms = (
                time.perf_counter() - t0
            ) * 1000.0

            return {
                "ok": True,
                "books": books,
                "latency_ms": latency_ms,
                "attempts": attempt,
                "error": None,
            }

        except Exception as exc:
            latency_ms = (
                time.perf_counter() - t0
            ) * 1000.0

            last_error = (
                f"{type(exc).__name__}: {exc}"
            )

            if attempt < MAX_RETRIES:
                time.sleep(attempt * 0.5)

    return {
        "ok": False,
        "books": [],
        "latency_ms": latency_ms,
        "attempts": MAX_RETRIES,
        "error": last_error,
    }


def classify_token_summaries(items):
    returned = [x for x in items if x is not None]

    if not returned:
        return "UNAVAILABLE"

    if len(returned) == 1:
        return "PARTIAL"

    states = [
        x["quote_state"]
        for x in returned
    ]

    if all(x == "TWO_SIDED" for x in states):
        return "TWO_SIDED"

    return "DEGRADED"


def end_class(end_date, now_dt):
    dt = parse_dt(end_date)

    if dt is None:
        return "UNKNOWN"

    days = (
        dt - now_dt
    ).total_seconds() / 86400.0

    if days <= 0:
        return "PAST_OR_DUE"

    if days <= 7:
        return "LE_7D"

    return "FUTURE_GT_7D"


def next_tier(
    previous_tier,
    state,
    bad_streak,
    end_date,
    now_dt,
):
    eclass = end_class(
        end_date,
        now_dt,
    )

    if eclass == "PAST_OR_DUE":
        return "COLD"

    if state == "TWO_SIDED":
        if eclass == "LE_7D":
            return "HOT"
        return "WARM"

    # Hysteresis for degraded/unavailable future markets.
    #
    # First bad observation:
    #   retain established HOT/WARM tier;
    #   newly-classified future markets enter WARM.
    #
    # Second/third consecutive bad:
    #   WARM.
    #
    # Fourth+ consecutive bad:
    #   COLD.
    if bad_streak >= 4:
        return "COLD"

    if bad_streak == 1:
        if previous_tier in ("HOT", "WARM"):
            return previous_tier
        return "WARM"

    return "WARM"


def schedule_for_tier(now_dt, tier):
    minutes = CADENCE_MINUTES[tier]
    return now_dt + timedelta(minutes=minutes)


def update_transport_error(
    con,
    row,
    now_dt,
    latency_ms,
    error,
):
    streak = int(
        row["clob_transport_error_streak"] or 0
    ) + 1

    con.execute("""
        UPDATE universe_markets
        SET clob_transport_error_streak = ?,
            clob_last_error = ?,
            clob_last_latency_ms = ?,
            clob_next_check_at = ?,
            clob_verification_schema = ?
        WHERE market_id = ?
    """, (
        streak,
        error,
        latency_ms,
        iso(
            now_dt + timedelta(
                minutes=TRANSPORT_RETRY_MINUTES
            )
        ),
        SCHEMA_VERSION,
        row["market_id"],
    ))


def update_observation(
    con,
    row,
    now_dt,
    state,
    returned_tokens,
    latency_ms,
):
    previous_tier = (
        row["tier"]
        if row["tier"] in ("HOT", "WARM", "COLD")
        else "UNASSIGNED"
    )

    if state == "TWO_SIDED":
        good_streak = int(
            row["clob_good_streak"] or 0
        ) + 1
        bad_streak = 0
    else:
        good_streak = 0
        bad_streak = int(
            row["clob_bad_streak"] or 0
        ) + 1

    tier = next_tier(
        previous_tier,
        state,
        bad_streak,
        row["end_date"],
        now_dt,
    )

    next_check = schedule_for_tier(
        now_dt,
        tier,
    )

    tier_updated_at = (
        iso(now_dt)
        if tier != previous_tier
        else None
    )

    con.execute("""
        UPDATE universe_markets
        SET clob_state = ?,
            tier = ?,
            clob_last_verified_at = ?,
            clob_next_check_at = ?,
            clob_good_streak = ?,
            clob_bad_streak = ?,
            clob_transport_error_streak = 0,
            clob_last_error = NULL,
            clob_last_latency_ms = ?,
            clob_last_returned_tokens = ?,
            clob_verification_schema = ?,
            tier_updated_at = COALESCE(?, tier_updated_at)
        WHERE market_id = ?
    """, (
        state,
        tier,
        iso(now_dt),
        iso(next_check),
        good_streak,
        bad_streak,
        latency_ms,
        returned_tokens,
        SCHEMA_VERSION,
        tier_updated_at,
        row["market_id"],
    ))


def main():
    parser = argparse.ArgumentParser(
        description=(
            "SignalAtlas canonical-universe "
            "CLOB verifier/scheduler v1"
        )
    )
    parser.add_argument(
        "--db",
        default=str(DEFAULT_DB),
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=1000,
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help=(
            "Persist schema/state/run accounting to the supplied "
            "offline universe DB"
        ),
    )
    parser.add_argument(
        "--sleep-ms",
        type=int,
        default=150,
    )

    args = parser.parse_args()

    db = Path(args.db).resolve()

    if not db.exists():
        raise SystemExit(
            f"DB_MISSING: {db}"
        )

    if args.limit < 1:
        raise SystemExit(
            "--limit must be >= 1"
        )

    lock = acquire_lock()

    try:
        if not args.apply:
            con = sqlite3.connect(
                f"file:{db}?mode=ro",
                uri=True,
            )
            con.row_factory = sqlite3.Row

            tables = {
                r[0]
                for r in con.execute("""
                    SELECT name
                    FROM sqlite_master
                    WHERE type='table'
                """)
            }

            if "universe_markets" not in tables:
                raise SystemExit(
                    "universe_markets missing"
                )

            count = con.execute("""
                SELECT COUNT(*)
                FROM universe_markets
                WHERE gamma_eligible = 1
            """).fetchone()[0]

            con.close()

            print(
                "UNIVERSE VERIFIER v1 PLAN ONLY"
            )
            print("db:", db)
            print(
                "gamma-eligible:", count
            )
            print("limit:", args.limit)
            print(
                "apply: false; no schema/network/writes"
            )
            return

        con = sqlite3.connect(
            db,
            timeout=30,
        )
        con.row_factory = sqlite3.Row
        con.execute(
            "PRAGMA busy_timeout=30000"
        )

        ensure_schema(con)

        now_dt = utcnow()
        abandoned_runs_reconciled = reconcile_abandoned_runs(
            con,
            now_dt,
        )
        now_iso = iso(now_dt)

        total_due = due_count(
            con,
            now_iso,
        )

        selected = select_due(
            con,
            now_iso,
            args.limit,
        )

        run_id = str(uuid.uuid4())
        started_at = iso(utcnow())

        con.execute("""
            INSERT INTO universe_clob_verification_runs (
                run_id,
                started_at,
                db_path,
                requested_limit,
                markets_selected,
                status,
                schema_version
            )
            VALUES (?, ?, ?, ?, ?, 'RUNNING', ?)
        """, (
            run_id,
            started_at,
            str(db),
            args.limit,
            len(selected),
            SCHEMA_VERSION,
        ))
        con.commit()

        if not selected:
            con.execute("""
                UPDATE universe_clob_verification_runs
                SET completed_at = ?,
                    status = 'COMPLETE_EMPTY',
                    wall_seconds = 0
                WHERE run_id = ?
            """, (
                iso(utcnow()),
                run_id,
            ))
            con.commit()
            print(
                "UNIVERSE VERIFIER v1: no due markets"
            )
            con.close()
            return

        market_map = {}
        token_ids = []

        for row in selected:
            tokens = [
                str(x)
                for x in safe_json_list(
                    row["clob_token_ids_json"]
                )
            ][:2]

            if len(tokens) < 2:
                # Should not happen for gamma_eligible=1.
                continue

            market_map[
                str(row["market_id"])
            ] = {
                "row": row,
                "tokens": tokens,
            }

            token_ids.extend(tokens)

        client = ClobClient(HOST)

        token_books = {}
        token_batch_error = {}
        token_latency = {}

        batches_ok = 0
        batches_failed = 0

        wall_t0 = time.perf_counter()

        for i in range(
            0,
            len(token_ids),
            BATCH_SIZE,
        ):
            chunk = token_ids[
                i:i + BATCH_SIZE
            ]

            result = fetch_batch(
                client,
                chunk,
            )

            if result["ok"]:
                batches_ok += 1

                for token in chunk:
                    token_latency[token] = (
                        result["latency_ms"]
                    )

                for book in result["books"]:
                    token = book_token(book)
                    if token:
                        token_books[token] = book

            else:
                batches_failed += 1

                for token in chunk:
                    token_batch_error[token] = (
                        result["error"]
                    )
                    token_latency[token] = (
                        result["latency_ms"]
                    )

            if args.sleep_ms > 0:
                time.sleep(
                    args.sleep_ms / 1000.0
                )

        state_counts = Counter()
        tier_counts = Counter()
        transport_errors = 0
        markets_processed = 0
        markets_committed = 0
        pending_updates = 0

        for market_id, item in market_map.items():
            row = item["row"]
            tokens = item["tokens"]

            if any(
                t in token_batch_error
                for t in tokens
            ):
                transport_errors += 1

                latency = max(
                    token_latency.get(t, 0.0)
                    for t in tokens
                )

                error = next(
                    token_batch_error[t]
                    for t in tokens
                    if t in token_batch_error
                )

                update_transport_error(
                    con,
                    row,
                    now_dt,
                    latency,
                    error,
                )

                markets_processed += 1
                pending_updates += 1

                if pending_updates >= UPDATE_COMMIT_CHUNK:
                    con.execute("""
                        UPDATE universe_clob_verification_runs
                        SET markets_processed = ?,
                            markets_committed = ?
                        WHERE run_id = ?
                    """, (
                        markets_processed,
                        markets_processed,
                        run_id,
                    ))
                    con.commit()
                    markets_committed = markets_processed
                    pending_updates = 0

                continue

            summaries = []
            returned_tokens = 0

            for token in tokens:
                book = token_books.get(token)

                if book is None:
                    summaries.append(None)
                else:
                    returned_tokens += 1
                    summaries.append(
                        summarize_book(book)
                    )

            state = classify_token_summaries(
                summaries
            )

            latency = max(
                token_latency.get(t, 0.0)
                for t in tokens
            )

            update_observation(
                con,
                row,
                now_dt,
                state,
                returned_tokens,
                latency,
            )

            state_counts[state] += 1
            markets_processed += 1
            pending_updates += 1

            if pending_updates >= UPDATE_COMMIT_CHUNK:
                con.execute("""
                    UPDATE universe_clob_verification_runs
                    SET markets_processed = ?,
                        markets_committed = ?
                    WHERE run_id = ?
                """, (
                    markets_processed,
                    markets_processed,
                    run_id,
                ))
                con.commit()
                markets_committed = markets_processed
                pending_updates = 0

        if pending_updates:
            con.execute("""
                UPDATE universe_clob_verification_runs
                SET markets_processed = ?,
                    markets_committed = ?
                WHERE run_id = ?
            """, (
                markets_processed,
                markets_processed,
                run_id,
            ))
            con.commit()
            markets_committed = markets_processed
            pending_updates = 0

        # Read resulting tiers for this run's selected markets.
        ids = list(market_map.keys())

        for i in range(0, len(ids), 500):
            chunk = ids[i:i + 500]
            placeholders = ",".join(
                "?" for _ in chunk
            )

            for r in con.execute(
                f"""
                SELECT tier, COUNT(*)
                FROM universe_markets
                WHERE market_id IN ({placeholders})
                GROUP BY tier
                """,
                chunk,
            ):
                tier_counts[r[0]] += r[1]

        wall_seconds = (
            time.perf_counter() - wall_t0
        )

        con.execute("""
            UPDATE universe_clob_verification_runs
            SET completed_at = ?,
                markets_processed = ?,
                markets_committed = ?,
                tokens_requested = ?,
                batches_total = ?,
                batches_ok = ?,
                batches_failed = ?,
                state_counts_json = ?,
                tier_counts_json = ?,
                wall_seconds = ?,
                status = 'COMPLETE'
            WHERE run_id = ?
        """, (
            iso(utcnow()),
            markets_processed,
            markets_committed,
            len(token_ids),
            batches_ok + batches_failed,
            batches_ok,
            batches_failed,
            json.dumps(
                dict(sorted(state_counts.items()))
            ),
            json.dumps(
                dict(sorted(tier_counts.items()))
            ),
            wall_seconds,
            run_id,
        ))
        con.commit()

        print(
            "UNIVERSE CLOB VERIFIER/SCHEDULER v1"
        )
        print("mode: CANONICAL / APPLY")
        print("db:", db)
        print("run_id:", run_id)
        print(
            "abandoned runs reconciled:",
            abandoned_runs_reconciled,
        )
        print("due before run:", total_due)
        print("selected:", len(selected))
        print("markets selected:", len(selected))
        print("markets processed:", markets_processed)
        print("markets committed:", markets_committed)
        print("tokens:", len(token_ids))
        print(
            "batches:",
            batches_ok + batches_failed,
            "ok=", batches_ok,
            "failed=", batches_failed,
        )
        print(
            "transport-error markets:",
            transport_errors,
        )
        print(
            "states:",
            dict(sorted(state_counts.items())),
        )
        print(
            "tiers:",
            dict(sorted(tier_counts.items())),
        )
        print(
            "wall seconds:",
            round(wall_seconds, 2),
        )
        print(
            "CANONICAL DB WRITES: YES"
        )

        con.close()

    except BaseException as exc:
        try:
            if "con" in locals():
                con.rollback()

                if "run_id" in locals():
                    con.execute("""
                        UPDATE universe_clob_verification_runs
                        SET completed_at = ?,
                            status = 'FAILED',
                            error_text = ?
                        WHERE run_id = ?
                          AND status = 'RUNNING'
                    """, (
                        iso(utcnow()),
                        f"{type(exc).__name__}: {exc}",
                        run_id,
                    ))
                    con.commit()
        except Exception:
            pass
        raise

    finally:
        lock.close()


if __name__ == "__main__":
    main()
