import json
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta, timezone

from .reliability_history import record_transition


DB = Path("analytics/market_measurements.sqlite3")
OUT = Path("analytics/system_status.json")

BUCKET_MINUTES = 15


def parse_ts(x):
    if not x:
        return None
    return datetime.fromisoformat(
        str(x).replace("Z", "+00:00")
    )


def age_seconds(ts, now):
    dt = parse_ts(ts)
    if dt is None:
        return None
    return round(
        max(0.0, (now - dt).total_seconds()),
        1,
    )


def table_exists(conn, name):
    return bool(
        conn.execute("""
            SELECT COUNT(*)
            FROM sqlite_master
            WHERE type = 'table'
              AND name = ?
        """, (name,)).fetchone()[0]
    )


def expected_buckets(first_raw, last_raw):
    first = parse_ts(first_raw)
    last = parse_ts(last_raw)

    if first is None or last is None:
        return []

    out = []
    cur = first

    while cur <= last:
        out.append(cur.isoformat())
        cur += timedelta(minutes=BUCKET_MINUTES)

    return out



def evaluate_reliability(now, gamma_bucket, clob_bucket,
                         gamma_tradable, clob_markets,
                         clob_token_rows, latest_run,
                         gamma_observed_at, clob_observed_at):
    """Current-bucket reliability; historical gaps remain separate."""
    current = now.replace(
        minute=(now.minute // BUCKET_MINUTES) * BUCKET_MINUTES,
        second=0,
        microsecond=0,
    )
    expected = current.isoformat()
    elapsed = (now - current).total_seconds()
    grace_seconds = 360
    reasons = []

    gamma_dt = parse_ts(gamma_bucket)
    clob_dt = parse_ts(clob_bucket)

    if gamma_dt and gamma_dt > current:
        reasons.append("FUTURE_GAMMA_BUCKET")
    if clob_dt and clob_dt > current:
        reasons.append("FUTURE_CLOB_BUCKET")

    if not gamma_dt or gamma_dt < current:
        reasons.append("GAMMA_CURRENT_BUCKET_MISSING")

    if not clob_dt or clob_dt < current:
        reasons.append("CLOB_CURRENT_BUCKET_MISSING")

    if gamma_bucket != clob_bucket:
        reasons.append("GAMMA_CLOB_BUCKET_MISMATCH")

    run = latest_run or {}
    if run.get("observation_bucket") != expected:
        reasons.append("CURRENT_CLOB_RUN_MISSING")
    else:
        if run.get("status") != "OK":
            reasons.append("CLOB_RUN_NOT_OK")
        requested = run.get("tokens_requested")
        returned = run.get("books_returned")
        if (not isinstance(requested, int)
                or requested <= 0
                or returned != requested
                or run.get("batch_failures") != 0
                or run.get("missing_tokens") != 0):
            reasons.append("CLOB_TOKEN_INCOMPLETE")
        if clob_token_rows != requested:
            reasons.append("CLOB_PERSISTED_TOKEN_MISMATCH")

    if gamma_bucket == expected and clob_bucket == expected:
        if gamma_tradable is None or gamma_tradable <= 0:
            reasons.append("GAMMA_TRADABLE_COUNT_INVALID")
        elif clob_markets != gamma_tradable:
            reasons.append("CLOB_MARKET_COVERAGE_INCOMPLETE")

    for name, ts in (
        ("GAMMA", gamma_observed_at),
        ("CLOB", clob_observed_at),
    ):
        dt = parse_ts(ts)
        if dt is None or dt.tzinfo is None:
            reasons.append(name + "_OBSERVATION_MISSING")
        elif dt > now + timedelta(seconds=60):
            reasons.append(name + "_OBSERVATION_FUTURE")
        elif (now - dt).total_seconds() > 1800:
            reasons.append(name + "_OBSERVATION_STALE")

    # Only missing/current-bucket synchronization can be pending.
    pending_reasons = {
        "GAMMA_CURRENT_BUCKET_MISSING",
        "CLOB_CURRENT_BUCKET_MISSING",
        "GAMMA_CLOB_BUCKET_MISMATCH",
        "CURRENT_CLOB_RUN_MISSING",
    }

    if not reasons:
        state = "HEALTHY"
    elif elapsed < grace_seconds and set(reasons) <= pending_reasons:
        state = "PENDING"
    else:
        state = "DEGRADED"

    return {
        "state": state,
        "expected_bucket": expected,
        "grace_seconds": grace_seconds,
        "reasons": reasons,
        "gamma_tradable_markets": gamma_tradable,
        "clob_measured_markets": clob_markets,
        "tradable_clob_coverage_fraction": (
            round(clob_markets / gamma_tradable, 6)
            if gamma_tradable and gamma_bucket == clob_bucket
            else None
        ),
        "coverage_scope": "latest_collected_gamma_slice",
    }


def main():
    now = datetime.now(timezone.utc)

    if not DB.exists():
        raise SystemExit("MEASUREMENT_DATABASE_MISSING")

    uri = f"file:{DB.resolve()}?mode=ro"

    with sqlite3.connect(uri, uri=True) as conn:
        # ---------- Gamma / canonical snapshots ----------
        snapshot_rows = conn.execute("""
            SELECT COUNT(*)
            FROM snapshots
        """).fetchone()[0]

        snapshot_markets = conn.execute("""
            SELECT COUNT(DISTINCT market_id)
            FROM snapshots
        """).fetchone()[0]

        snapshot_buckets = conn.execute("""
            SELECT COUNT(DISTINCT observation_bucket)
            FROM snapshots
        """).fetchone()[0]

        first_gamma_bucket, latest_gamma_bucket = conn.execute("""
            SELECT
                MIN(observation_bucket),
                MAX(observation_bucket)
            FROM snapshots
        """).fetchone()

        latest_gamma_observed_at = conn.execute("""
            SELECT MAX(observed_at)
            FROM snapshots
        """).fetchone()[0]

        gamma_latest_rows = 0
        gamma_latest_states = []

        if latest_gamma_bucket:
            gamma_latest_rows = conn.execute("""
                SELECT COUNT(*)
                FROM snapshots
                WHERE observation_bucket = ?
            """, (latest_gamma_bucket,)).fetchone()[0]

            gamma_latest_states = conn.execute("""
                SELECT quote_state, COUNT(*)
                FROM snapshots
                WHERE observation_bucket = ?
                GROUP BY quote_state
                ORDER BY quote_state
            """, (latest_gamma_bucket,)).fetchall()

        actual_gamma_buckets = {
            row[0]
            for row in conn.execute("""
                SELECT DISTINCT observation_bucket
                FROM snapshots
            """).fetchall()
        }

        expected = expected_buckets(
            first_gamma_bucket,
            latest_gamma_bucket,
        )

        missing_gamma_buckets = [
            b for b in expected
            if b not in actual_gamma_buckets
        ]

        # ---------- CLOB ----------
        clob = {
            "table_present": False,
            "rows": 0,
            "buckets": 0,
            "first_bucket": None,
            "latest_bucket": None,
            "latest_observed_at": None,
            "latest_token_rows": 0,
            "latest_markets": 0,
            "latest_collection_status": [],
            "latest_quote_states": [],
            "total_runs": 0,
            "partial_runs": 0,
            "latest_run": None,
            "missing_buckets_since_clob_start": [],
        }

        if table_exists(conn, "clob_books"):
            clob["table_present"] = True

            clob["rows"] = conn.execute("""
                SELECT COUNT(*)
                FROM clob_books
            """).fetchone()[0]

            clob["buckets"] = conn.execute("""
                SELECT COUNT(DISTINCT observation_bucket)
                FROM clob_books
            """).fetchone()[0]

            (
                clob["first_bucket"],
                clob["latest_bucket"],
            ) = conn.execute("""
                SELECT
                    MIN(observation_bucket),
                    MAX(observation_bucket)
                FROM clob_books
            """).fetchone()

            clob["latest_observed_at"] = conn.execute("""
                SELECT MAX(observed_at)
                FROM clob_books
            """).fetchone()[0]

            if clob["latest_bucket"]:
                clob["latest_token_rows"] = conn.execute("""
                    SELECT COUNT(*)
                    FROM clob_books
                    WHERE observation_bucket = ?
                """, (
                    clob["latest_bucket"],
                )).fetchone()[0]

                clob["latest_markets"] = conn.execute("""
                    SELECT COUNT(DISTINCT market_id)
                    FROM clob_books
                    WHERE observation_bucket = ?
                """, (
                    clob["latest_bucket"],
                )).fetchone()[0]

                clob["latest_collection_status"] = conn.execute("""
                    SELECT collection_status, COUNT(*)
                    FROM clob_books
                    WHERE observation_bucket = ?
                    GROUP BY collection_status
                    ORDER BY collection_status
                """, (
                    clob["latest_bucket"],
                )).fetchall()

                clob["latest_quote_states"] = conn.execute("""
                    SELECT quote_state, COUNT(*)
                    FROM clob_books
                    WHERE observation_bucket = ?
                      AND collection_status = 'OK'
                    GROUP BY quote_state
                    ORDER BY quote_state
                """, (
                    clob["latest_bucket"],
                )).fetchall()

            if clob["first_bucket"]:
                gamma_since_clob = {
                    row[0]
                    for row in conn.execute("""
                        SELECT DISTINCT observation_bucket
                        FROM snapshots
                        WHERE observation_bucket >= ?
                    """, (
                        clob["first_bucket"],
                    )).fetchall()
                }

                clob_buckets_set = {
                    row[0]
                    for row in conn.execute("""
                        SELECT DISTINCT observation_bucket
                        FROM clob_books
                        WHERE observation_bucket >= ?
                    """, (
                        clob["first_bucket"],
                    )).fetchall()
                }

                clob["missing_buckets_since_clob_start"] = sorted(
                    gamma_since_clob - clob_buckets_set
                )

        if table_exists(conn, "clob_collection_runs"):
            clob["total_runs"] = conn.execute("""
                SELECT COUNT(*)
                FROM clob_collection_runs
            """).fetchone()[0]

            clob["partial_runs"] = conn.execute("""
                SELECT COUNT(*)
                FROM clob_collection_runs
                WHERE status != 'OK'
            """).fetchone()[0]

            latest_run = conn.execute("""
                SELECT
                    observation_bucket,
                    tokens_requested,
                    books_returned,
                    batch_failures,
                    missing_tokens,
                    status,
                    latency_ms,
                    completed_at
                FROM clob_collection_runs
                ORDER BY completed_at DESC
                LIMIT 1
            """).fetchone()

            if latest_run:
                clob["latest_run"] = {
                    "observation_bucket": latest_run[0],
                    "tokens_requested": latest_run[1],
                    "books_returned": latest_run[2],
                    "batch_failures": latest_run[3],
                    "missing_tokens": latest_run[4],
                    "status": latest_run[5],
                    "latency_ms": latest_run[6],
                    "completed_at": latest_run[7],
                }

        # ---------- Forward outcomes ----------
        forward = {
            "table_present": False,
            "total_rows": 0,
            "by_horizon": [],
            "by_status": [],
            "latest_created_at": None,
        }

        if table_exists(conn, "forward_outcomes"):
            forward["table_present"] = True

            forward["total_rows"] = conn.execute("""
                SELECT COUNT(*)
                FROM forward_outcomes
            """).fetchone()[0]

            forward["by_horizon"] = conn.execute("""
                SELECT horizon_minutes, COUNT(*)
                FROM forward_outcomes
                GROUP BY horizon_minutes
                ORDER BY horizon_minutes
            """).fetchall()

            forward["by_status"] = conn.execute("""
                SELECT label_status, COUNT(*)
                FROM forward_outcomes
                GROUP BY label_status
                ORDER BY label_status
            """).fetchall()

            forward["latest_created_at"] = conn.execute("""
                SELECT MAX(created_at)
                FROM forward_outcomes
            """).fetchone()[0]

    gamma_tradable = None
    if latest_gamma_bucket:
        with sqlite3.connect(uri, uri=True) as conn:
            gamma_tradable = conn.execute("""
                SELECT COUNT(DISTINCT market_id)
                FROM snapshots
                WHERE observation_bucket = ?
                  AND tradable_top_of_book = 1
            """, (latest_gamma_bucket,)).fetchone()[0]

    reliability = evaluate_reliability(
        now,
        latest_gamma_bucket,
        clob["latest_bucket"],
        gamma_tradable,
        clob["latest_markets"],
        clob["latest_token_rows"],
        clob["latest_run"],
        latest_gamma_observed_at,
        clob["latest_observed_at"],
    )

    out = {
        "reliability": reliability,
        "schema_version": "signalatlas_measurement_health_v1",
        "generated_at": now.isoformat(),

        "database": {
            "path": str(DB),
            "size_bytes": DB.stat().st_size,
        },

        "gamma": {
            "snapshot_rows": snapshot_rows,
            "unique_markets": snapshot_markets,
            "bucket_count": snapshot_buckets,

            "first_bucket": first_gamma_bucket,
            "latest_bucket": latest_gamma_bucket,
            "latest_observed_at":
                latest_gamma_observed_at,

            "latest_bucket_rows":
                gamma_latest_rows,

            "latest_quote_states": [
                {
                    "quote_state": state,
                    "count": count,
                }
                for state, count in gamma_latest_states
            ],

            "missing_bucket_count":
                len(missing_gamma_buckets),

            "missing_buckets":
                missing_gamma_buckets[-20:],

            "collector_freshness_seconds":
                age_seconds(
                    latest_gamma_observed_at,
                    now,
                ),
        },

        "clob": {
            **{
                k: v for k, v in clob.items()
                if k not in (
                    "latest_collection_status",
                    "latest_quote_states",
                )
            },

            "latest_collection_status": [
                {
                    "status": state,
                    "count": count,
                }
                for state, count
                in clob["latest_collection_status"]
            ],

            "latest_quote_states": [
                {
                    "quote_state": state,
                    "count": count,
                }
                for state, count
                in clob["latest_quote_states"]
            ],

            "collector_freshness_seconds":
                age_seconds(
                    clob["latest_observed_at"],
                    now,
                ),
        },

        "alignment": {
            "latest_gamma_bucket":
                latest_gamma_bucket,

            "latest_clob_bucket":
                clob["latest_bucket"],

            "gamma_clob_same_latest_bucket":
                bool(
                    latest_gamma_bucket
                    and clob["latest_bucket"]
                    and latest_gamma_bucket
                    == clob["latest_bucket"]
                ),
        },

        "forward_outcomes": {
            "table_present":
                forward["table_present"],

            "total_rows":
                forward["total_rows"],

            "by_horizon": [
                {
                    "horizon_minutes": horizon,
                    "count": count,
                }
                for horizon, count
                in forward["by_horizon"]
            ],

            "by_status": [
                {
                    "label_status": status,
                    "count": count,
                }
                for status, count
                in forward["by_status"]
            ],

            "latest_created_at":
                forward["latest_created_at"],
        },
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)

    tmp = OUT.with_suffix(".json.tmp")
    tmp.write_text(
        json.dumps(out, indent=2),
        encoding="utf-8",
    )
    tmp.replace(OUT)

    try:
        record_transition(
            OUT.parent / "reliability_incidents.jsonl",
            out["generated_at"],
            reliability["state"],
            reliability["reasons"],
        )
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"[RELIABILITY_HISTORY_ERROR] {exc}")

    print("SIGNALATLAS MEASUREMENT HEALTH")
    print("gamma_latest =", latest_gamma_bucket)
    print("gamma_buckets =", snapshot_buckets)
    print(
        "gamma_missing_buckets =",
        len(missing_gamma_buckets),
    )
    print("clob_latest =", clob["latest_bucket"])
    print("clob_runs =", clob["total_runs"])
    print("clob_partial_runs =", clob["partial_runs"])
    print(
        "gamma_clob_aligned =",
        out["alignment"][
            "gamma_clob_same_latest_bucket"
        ],
    )
    print(
        "forward_rows =",
        forward["total_rows"],
    )
    print(
        "db_bytes =",
        DB.stat().st_size,
    )
    print("file =", OUT)


if __name__ == "__main__":
    main()
