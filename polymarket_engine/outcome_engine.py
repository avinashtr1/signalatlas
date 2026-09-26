import sqlite3
from pathlib import Path
from datetime import datetime, timedelta, timezone


DB = Path("analytics/market_measurements.sqlite3")

HORIZONS = (60, 360, 1440)  # 1h, 6h, 24h
MAX_LABEL_LATENESS_MINUTES = 20


def parse_ts(x):
    return datetime.fromisoformat(x.replace("Z", "+00:00"))


def init_db(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS forward_outcomes (
            market_id TEXT NOT NULL,
            market_name TEXT,

            base_observation_bucket TEXT NOT NULL,
            base_observed_at TEXT NOT NULL,
            base_reference_price REAL,
            base_best_bid REAL,
            base_best_ask REAL,
            base_mid_price REAL,
            base_spread REAL,

            horizon_minutes INTEGER NOT NULL,
            target_bucket TEXT NOT NULL,

            label_status TEXT NOT NULL,

            future_observation_bucket TEXT,
            future_observed_at TEXT,
            horizon_error_seconds REAL,

            future_reference_price REAL,
            future_best_bid REAL,
            future_best_ask REAL,
            future_mid_price REAL,
            future_spread REAL,
            future_quote_state TEXT,
            future_tradable_top_of_book INTEGER,

            created_at TEXT NOT NULL,

            PRIMARY KEY (
                market_id,
                base_observation_bucket,
                horizon_minutes
            )
        )
    """)

    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_forward_horizon_status
        ON forward_outcomes (
            horizon_minutes,
            label_status
        )
    """)

    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_forward_market_base
        ON forward_outcomes (
            market_id,
            base_observation_bucket
        )
    """)


def main():
    if not DB.exists():
        raise SystemExit("MEASUREMENT_DATABASE_MISSING")

    now = datetime.now(timezone.utc)

    with sqlite3.connect(DB) as conn:
        conn.row_factory = sqlite3.Row
        init_db(conn)

        latest_bucket_raw = conn.execute("""
            SELECT MAX(observation_bucket)
            FROM snapshots
        """).fetchone()[0]

        if not latest_bucket_raw:
            raise SystemExit("NO_MEASUREMENT_HISTORY")

        latest_bucket = parse_ts(latest_bucket_raw)

        bases = conn.execute("""
            SELECT *
            FROM snapshots
            WHERE tradable_top_of_book = 1
              AND quote_state = 'TWO_SIDED'
              AND best_bid IS NOT NULL
              AND best_ask IS NOT NULL
              AND mid_price IS NOT NULL
        """).fetchall()

        inserted = 0
        labeled = 0
        missing = 0
        pending = 0

        for base in bases:
            base_bucket = parse_ts(
                base["observation_bucket"]
            )

            for horizon_minutes in HORIZONS:
                target = base_bucket + timedelta(
                    minutes=horizon_minutes
                )

                grace_end = target + timedelta(
                    minutes=MAX_LABEL_LATENESS_MINUTES
                )

                # Horizon has not matured enough yet.
                if latest_bucket < target:
                    pending += 1
                    continue

                future = conn.execute("""
                    SELECT *
                    FROM snapshots
                    WHERE market_id = ?
                      AND observation_bucket >= ?
                      AND observation_bucket <= ?
                    ORDER BY observation_bucket ASC
                    LIMIT 1
                """, (
                    base["market_id"],
                    target.isoformat(),
                    grace_end.isoformat(),
                )).fetchone()

                if future is not None:
                    future_bucket = parse_ts(
                        future["observation_bucket"]
                    )

                    error_seconds = (
                        future_bucket - target
                    ).total_seconds()

                    status = (
                        "OBSERVED_" +
                        str(future["quote_state"])
                    )

                    values = {
                        "market_id": base["market_id"],
                        "market_name": base["market_name"],

                        "base_observation_bucket":
                            base["observation_bucket"],
                        "base_observed_at":
                            base["observed_at"],
                        "base_reference_price":
                            base["reference_price"],
                        "base_best_bid":
                            base["best_bid"],
                        "base_best_ask":
                            base["best_ask"],
                        "base_mid_price":
                            base["mid_price"],
                        "base_spread":
                            base["spread"],

                        "horizon_minutes":
                            horizon_minutes,
                        "target_bucket":
                            target.isoformat(),

                        "label_status": status,

                        "future_observation_bucket":
                            future["observation_bucket"],
                        "future_observed_at":
                            future["observed_at"],
                        "horizon_error_seconds":
                            error_seconds,

                        "future_reference_price":
                            future["reference_price"],
                        "future_best_bid":
                            future["best_bid"],
                        "future_best_ask":
                            future["best_ask"],
                        "future_mid_price":
                            future["mid_price"],
                        "future_spread":
                            future["spread"],
                        "future_quote_state":
                            future["quote_state"],
                        "future_tradable_top_of_book":
                            future["tradable_top_of_book"],

                        "created_at": now.isoformat(),
                    }

                    result = conn.execute("""
                        INSERT OR IGNORE INTO forward_outcomes (
                            market_id,
                            market_name,

                            base_observation_bucket,
                            base_observed_at,
                            base_reference_price,
                            base_best_bid,
                            base_best_ask,
                            base_mid_price,
                            base_spread,

                            horizon_minutes,
                            target_bucket,

                            label_status,

                            future_observation_bucket,
                            future_observed_at,
                            horizon_error_seconds,

                            future_reference_price,
                            future_best_bid,
                            future_best_ask,
                            future_mid_price,
                            future_spread,
                            future_quote_state,
                            future_tradable_top_of_book,

                            created_at
                        )
                        VALUES (
                            :market_id,
                            :market_name,

                            :base_observation_bucket,
                            :base_observed_at,
                            :base_reference_price,
                            :base_best_bid,
                            :base_best_ask,
                            :base_mid_price,
                            :base_spread,

                            :horizon_minutes,
                            :target_bucket,

                            :label_status,

                            :future_observation_bucket,
                            :future_observed_at,
                            :horizon_error_seconds,

                            :future_reference_price,
                            :future_best_bid,
                            :future_best_ask,
                            :future_mid_price,
                            :future_spread,
                            :future_quote_state,
                            :future_tradable_top_of_book,

                            :created_at
                        )
                    """, values)

                    if result.rowcount:
                        inserted += 1
                        labeled += 1

                    continue

                # Do not call an observation missing until the
                # full grace interval has passed.
                if latest_bucket >= grace_end:
                    values = {
                        "market_id": base["market_id"],
                        "market_name": base["market_name"],

                        "base_observation_bucket":
                            base["observation_bucket"],
                        "base_observed_at":
                            base["observed_at"],
                        "base_reference_price":
                            base["reference_price"],
                        "base_best_bid":
                            base["best_bid"],
                        "base_best_ask":
                            base["best_ask"],
                        "base_mid_price":
                            base["mid_price"],
                        "base_spread":
                            base["spread"],

                        "horizon_minutes":
                            horizon_minutes,
                        "target_bucket":
                            target.isoformat(),

                        "label_status":
                            "MISSING_IN_COLLECTED_SCOPE",

                        "created_at": now.isoformat(),
                    }

                    result = conn.execute("""
                        INSERT OR IGNORE INTO forward_outcomes (
                            market_id,
                            market_name,

                            base_observation_bucket,
                            base_observed_at,
                            base_reference_price,
                            base_best_bid,
                            base_best_ask,
                            base_mid_price,
                            base_spread,

                            horizon_minutes,
                            target_bucket,

                            label_status,
                            created_at
                        )
                        VALUES (
                            :market_id,
                            :market_name,

                            :base_observation_bucket,
                            :base_observed_at,
                            :base_reference_price,
                            :base_best_bid,
                            :base_best_ask,
                            :base_mid_price,
                            :base_spread,

                            :horizon_minutes,
                            :target_bucket,

                            :label_status,
                            :created_at
                        )
                    """, values)

                    if result.rowcount:
                        inserted += 1
                        missing += 1
                else:
                    pending += 1

        conn.commit()

        total = conn.execute("""
            SELECT COUNT(*)
            FROM forward_outcomes
        """).fetchone()[0]

        print("FORWARD_OUTCOME_ENGINE")
        print("base_tradable_snapshots =", len(bases))
        print("latest_measurement_bucket =", latest_bucket_raw)
        print("new_rows =", inserted)
        print("new_observed_labels =", labeled)
        print("new_missing_labels =", missing)
        print("pending_horizon_checks =", pending)
        print("total_forward_labels =", total)


if __name__ == "__main__":
    main()
