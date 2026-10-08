import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException, Query


ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "analytics" / "market_measurements.sqlite3"
HEALTH = ROOT / "analytics" / "system_status.json"

API_VERSION = "2.1.0"

SNAPSHOT_BOOL_FIELDS = {
    "two_sided",
    "tradable_top_of_book",
    "active",
    "closed",
    "archived",
    "accepting_orders",
    "neg_risk",
    "neg_risk_augmented",
    "resolution_time_valid",
}

FORWARD_BOOL_FIELDS = {
    "future_tradable_top_of_book",
}


app = FastAPI(
    title="SignalAtlas Measurement API",
    version=API_VERSION,
    description=(
        "Read-only canonical SignalAtlas measurement interface. "
        "Backed exclusively by the certified measurement SQLite database."
    ),
)


def connect():
    if not DB.exists():
        raise HTTPException(
            status_code=503,
            detail="measurement_database_missing",
        )

    uri = f"file:{DB.resolve()}?mode=ro"

    try:
        conn = sqlite3.connect(
            uri,
            uri=True,
            timeout=5.0,
        )
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA query_only = ON")
        conn.execute("PRAGMA busy_timeout = 5000")
        return conn
    except sqlite3.Error as exc:
        raise HTTPException(
            status_code=503,
            detail=f"measurement_database_unavailable: {exc}",
        )


def row_dict(row, bool_fields=None):
    if row is None:
        return None

    out = dict(row)

    for field in bool_fields or ():
        if field in out and out[field] is not None:
            out[field] = bool(out[field])

    return out


def latest_snapshot_bucket(conn):
    row = conn.execute("""
        SELECT MAX(observation_bucket)
        FROM snapshots
    """).fetchone()

    return row[0] if row else None


def market_exists(conn, market_id):
    return bool(
        conn.execute("""
            SELECT 1
            FROM snapshots
            WHERE market_id = ?
            LIMIT 1
        """, (market_id,)).fetchone()
    )


def source_scope():
    return {
        "complete_universe": False,
        "coverage": "partial_event_slice",
        "note": (
            "Current canonical collector samples a bounded active-event "
            "slice; this API must not be interpreted as complete "
            "Polymarket universe coverage."
        ),
    }


def resolution_scope():
    return {
        "complete_universe": False,
        "coverage": "historically_observed_signalatlas_markets",
        "note": (
            "Resolution Truth tracks markets historically observed by "
            "SignalAtlas. This is broader than the current active-event "
            "measurement slice, but must not be interpreted as complete "
            "Polymarket universe coverage."
        ),
    }


def canonical_json(value, field):
    if value is None:
        return None

    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError) as exc:
        raise HTTPException(
            status_code=500,
            detail=f"canonical_json_invalid:{field}: {exc}",
        )


def resolution_watch_record(row):
    r = dict(row)

    return {
        "market_id": r["market_id"],
        "market_name": r["market_name"],
        "market_state": {
            "first_observed_at": r["first_observed_at"],
            "last_snapshot_at": r["last_snapshot_at"],
            "active": (
                None
                if r["latest_active"] is None
                else bool(r["latest_active"])
            ),
            "closed": (
                None
                if r["latest_closed"] is None
                else bool(r["latest_closed"])
            ),
        },
        "identity": {
            "status": r["identity_status"],
            "condition_id": r["condition_id"],
            "outcomes": canonical_json(
                r["outcomes_json"],
                "resolution_watch.outcomes_json",
            ),
            "source": r["identity_source"],
            "last_checked_at": r[
                "last_identity_checked_at"
            ],
        },
        "chain": {
            "status": r["chain_status"],
            "last_checked_at": r[
                "last_chain_checked_at"
            ],
            "last_checked_block": r[
                "last_chain_checked_block"
            ],
            "last_error": r["last_error"],
        },
        "schema_version": r["schema_version"],
        "updated_at": r["updated_at"],
    }


def resolution_record(row):
    r = dict(row)

    return {
        "market_id": r["market_id"],
        "market_name": r["market_name"],
        "identity": {
            "condition_id": r["condition_id"],
            "outcomes": canonical_json(
                r["outcomes_json"],
                "market_resolutions.outcomes_json",
            ),
        },
        "payout": {
            "denominator_raw": r[
                "payout_denominator_raw"
            ],
            "numerators_raw": canonical_json(
                r["payout_numerators_json"],
                (
                    "market_resolutions."
                    "payout_numerators_json"
                ),
            ),
            "normalized": canonical_json(
                r["normalized_payouts_json"],
                (
                    "market_resolutions."
                    "normalized_payouts_json"
                ),
            ),
            "positive_indices": canonical_json(
                r["positive_payout_indices_json"],
                (
                    "market_resolutions."
                    "positive_payout_indices_json"
                ),
            ),
            "positive_labels": canonical_json(
                r["positive_payout_labels_json"],
                (
                    "market_resolutions."
                    "positive_payout_labels_json"
                ),
            ),
        },
        "first_observed_resolved_at": r[
            "first_observed_resolved_at"
        ],
        "source": {
            "chain_id": r["source_chain_id"],
            "contract": r["source_contract"],
            "method": r["source_method"],
        },
        "evidence": {
            "resolution_time": r["resolution_time"],
            "resolution_time_valid": (
                None
                if r["resolution_time_valid"] is None
                else bool(r["resolution_time_valid"])
            ),
            "resolution_time_source": r[
                "resolution_time_source"
            ],
            "resolution_block": r[
                "resolution_block"
            ],
            "resolution_tx_hash": r[
                "resolution_tx_hash"
            ],
            "resolution_log_index": r[
                "resolution_log_index"
            ],
            "status": r[
                "resolution_evidence_status"
            ],
        },
        "schema_version": r["schema_version"],
    }


@app.get("/")
def root():
    return {
        "service": "SignalAtlas Measurement API",
        "api_version": API_VERSION,
        "mode": "read_only",
        "database": "market_measurements.sqlite3",
        "source_scope": source_scope(),
        "resolution_scope": resolution_scope(),
        "docs": "/docs",
        "routes": [
            "/api/health",
            "/api/meta",
            "/api/markets",
            "/api/market/{market_id}",
            "/api/orderbook/{market_id}",
            "/api/measurements/{market_id}",
            "/api/forward-outcomes/{market_id}",
            "/api/resolution-status/{market_id}",
            "/api/resolution/{market_id}",
            "/api/resolutions",
        ],
    }


@app.get("/api/health")
def health():
    if not HEALTH.exists():
        raise HTTPException(
            status_code=503,
            detail="measurement_health_not_ready",
        )

    try:
        measurement = json.loads(
            HEALTH.read_text(encoding="utf-8")
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"measurement_health_invalid: {exc}",
        )

    # Phase 7B.65: fail closed on stale health reports.
    try:
        generated = datetime.fromisoformat(
            measurement["generated_at"]
        )
        if generated.tzinfo is None:
            raise ValueError("timezone_missing")
        age_seconds = (
            datetime.now(timezone.utc) - generated
        ).total_seconds()
    except (KeyError, TypeError, ValueError):
        raise HTTPException(
            status_code=503,
            detail="measurement_health_timestamp_invalid",
        )

    if age_seconds < -60:
        raise HTTPException(
            status_code=503,
            detail="measurement_health_timestamp_future",
        )

    if age_seconds > 1800:
        raise HTTPException(
            status_code=503,
            detail="measurement_health_stale",
        )

    return {
        "service": "SignalAtlas Measurement API",
        "api_version": API_VERSION,
        "mode": "read_only",
        "generated_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "measurement": measurement,
    }


@app.get("/api/markets")
def markets(
    limit: int = Query(100, ge=1, le=2000),
    offset: int = Query(0, ge=0),
    tradable: bool | None = Query(None),
    active: bool | None = Query(None),
    quote_state: str | None = Query(None),
):
    with connect() as conn:
        bucket = latest_snapshot_bucket(conn)

        if not bucket:
            raise HTTPException(
                status_code=503,
                detail="no_snapshot_measurements",
            )

        conditions = [
            "observation_bucket = ?"
        ]
        params = [bucket]

        if tradable is not None:
            conditions.append(
                "tradable_top_of_book = ?"
            )
            params.append(int(tradable))

        if active is not None:
            conditions.append(
                "active = ?"
            )
            params.append(int(active))

        if quote_state is not None:
            conditions.append(
                "quote_state = ?"
            )
            params.append(quote_state)

        where = " AND ".join(conditions)

        total = conn.execute(
            f"""
            SELECT COUNT(*)
            FROM snapshots
            WHERE {where}
            """,
            params,
        ).fetchone()[0]

        rows = conn.execute(
            f"""
            SELECT *
            FROM snapshots
            WHERE {where}
            ORDER BY
                COALESCE(volume_total_usd, -1) DESC,
                market_id ASC
            LIMIT ? OFFSET ?
            """,
            [*params, limit, offset],
        ).fetchall()

    return {
        "observation_bucket": bucket,
        "total_matching": total,
        "limit": limit,
        "offset": offset,
        "source_scope": source_scope(),
        "rows": [
            row_dict(
                r,
                SNAPSHOT_BOOL_FIELDS,
            )
            for r in rows
        ],
    }


@app.get("/api/market/{market_id}")
def market(market_id: str):
    with connect() as conn:
        row = conn.execute("""
            SELECT *
            FROM snapshots
            WHERE market_id = ?
            ORDER BY observation_bucket DESC
            LIMIT 1
        """, (market_id,)).fetchone()

    if row is None:
        raise HTTPException(
            status_code=404,
            detail="market_not_found",
        )

    return {
        "source_scope": source_scope(),
        "market": row_dict(
            row,
            SNAPSHOT_BOOL_FIELDS,
        ),
    }


@app.get("/api/orderbook/{market_id}")
def orderbook(market_id: str):
    with connect() as conn:
        if not market_exists(conn, market_id):
            raise HTTPException(
                status_code=404,
                detail="market_not_found",
            )

        latest_gamma_bucket = latest_snapshot_bucket(conn)

        bucket_row = conn.execute("""
            SELECT MAX(observation_bucket)
            FROM clob_books
            WHERE market_id = ?
        """, (market_id,)).fetchone()

        bucket = (
            bucket_row[0]
            if bucket_row
            else None
        )

        if not bucket:
            raise HTTPException(
                status_code=404,
                detail="no_clob_measurement",
            )

        rows = conn.execute("""
            SELECT *
            FROM clob_books
            WHERE market_id = ?
              AND observation_bucket = ?
            ORDER BY outcome_side ASC
        """, (
            market_id,
            bucket,
        )).fetchall()

    return {
        "market_id": market_id,
        "observation_bucket": bucket,
        "latest_gamma_bucket": latest_gamma_bucket,
        "book_observation_bucket": bucket,
        "is_current_bucket": bucket == latest_gamma_bucket,
        "freshness_status": (
            "CURRENT"
            if bucket == latest_gamma_bucket
            else "STALE"
        ),
        "token_books": [
            row_dict(r)
            for r in rows
        ],
    }


@app.get("/api/measurements/{market_id}")
def measurements(
    market_id: str,
    limit: int = Query(96, ge=1, le=2000),
):
    with connect() as conn:
        rows = conn.execute("""
            SELECT *
            FROM snapshots
            WHERE market_id = ?
            ORDER BY observation_bucket DESC
            LIMIT ?
        """, (
            market_id,
            limit,
        )).fetchall()

    if not rows:
        raise HTTPException(
            status_code=404,
            detail="market_not_found",
        )

    return {
        "market_id": market_id,
        "count": len(rows),
        "limit": limit,
        "source_scope": source_scope(),
        "rows": [
            row_dict(
                r,
                SNAPSHOT_BOOL_FIELDS,
            )
            for r in rows
        ],
    }


@app.get("/api/forward-outcomes/{market_id}")
def forward_outcomes(
    market_id: str,
    limit: int = Query(500, ge=1, le=5000),
):
    with connect() as conn:
        if not market_exists(conn, market_id):
            raise HTTPException(
                status_code=404,
                detail="market_not_found",
            )

        rows = conn.execute("""
            SELECT *
            FROM forward_outcomes
            WHERE market_id = ?
            ORDER BY
                base_observation_bucket DESC,
                horizon_minutes ASC
            LIMIT ?
        """, (
            market_id,
            limit,
        )).fetchall()

    return {
        "market_id": market_id,
        "count": len(rows),
        "limit": limit,
        "rows": [
            row_dict(
                r,
                FORWARD_BOOL_FIELDS,
            )
            for r in rows
        ],
    }


@app.get("/api/meta")
def meta():
    with connect() as conn:
        snapshot_bucket = latest_snapshot_bucket(conn)

        coverage = conn.execute("""
            SELECT
                COUNT(DISTINCT s.market_id)
                    AS gamma_observed,
                COUNT(DISTINCT CASE
                    WHEN s.tradable_top_of_book = 1
                    THEN s.market_id
                END) AS gamma_tradable,
                COUNT(DISTINCT c.market_id)
                    AS clob_measured,
                COUNT(DISTINCT CASE
                    WHEN s.tradable_top_of_book = 1
                    THEN c.market_id
                END) AS tradable_with_clob
            FROM snapshots s
            LEFT JOIN clob_books c
              ON c.market_id = s.market_id
             AND c.observation_bucket = s.observation_bucket
             AND c.collection_status = 'OK'
            WHERE s.observation_bucket = ?
        """, (snapshot_bucket,)).fetchone()

        clob_run = conn.execute("""
            SELECT status, completed_at
            FROM clob_collection_runs
            WHERE observation_bucket = ?
            ORDER BY completed_at DESC
            LIMIT 1
        """, (snapshot_bucket,)).fetchone()

        collection_state = (
            "PENDING" if clob_run is None
            or clob_run["completed_at"] is None
            else "COMPLETE" if clob_run["status"] == "OK"
            else "FAILED"
        )

        watch = conn.execute("""
            SELECT
                COUNT(*) AS total,
                COALESCE(
                    SUM(
                        CASE
                            WHEN identity_status = 'READY'
                            THEN 1 ELSE 0
                        END
                    ),
                    0
                ) AS identity_ready,
                COALESCE(
                    SUM(
                        CASE
                            WHEN chain_status = 'UNRESOLVED'
                            THEN 1 ELSE 0
                        END
                    ),
                    0
                ) AS chain_unresolved,
                COALESCE(
                    SUM(
                        CASE
                            WHEN chain_status = 'RESOLVED'
                            THEN 1 ELSE 0
                        END
                    ),
                    0
                ) AS chain_resolved,
                MAX(updated_at) AS latest_updated_at,
                MAX(last_chain_checked_at)
                    AS latest_chain_checked_at,
                MAX(last_chain_checked_block)
                    AS latest_chain_checked_block
            FROM resolution_watch
        """).fetchone()

        resolutions = conn.execute("""
            SELECT
                COUNT(*) AS total,
                MAX(first_observed_resolved_at)
                    AS latest_observed_resolved_at,
                MAX(resolution_time)
                    AS latest_valid_resolution_time
            FROM market_resolutions
        """).fetchone()

    return {
        "service": "SignalAtlas Measurement API",
        "api_version": API_VERSION,
        "mode": "read_only",
        "backing_store": (
            "analytics/market_measurements.sqlite3"
        ),
        "source_scope": source_scope(),
        "resolution_scope": resolution_scope(),
        "measurement_coverage": {
            "observation_bucket": snapshot_bucket,
            "complete_universe": False,
            "collection_state": collection_state,
            "collection_run_status": (
                clob_run["status"] if clob_run else None
            ),
            "collection_completed_at": (
                clob_run["completed_at"] if clob_run else None
            ),
            "gamma_observed_markets": coverage["gamma_observed"],
            "gamma_tradable_markets": coverage["gamma_tradable"],
            "clob_measured_markets": coverage["clob_measured"],
            "tradable_with_clob": coverage["tradable_with_clob"],
            "tradable_clob_coverage_fraction": (
                coverage["tradable_with_clob"]
                / coverage["gamma_tradable"]
                if (
                    collection_state == "COMPLETE"
                    and coverage["gamma_tradable"]
                )
                else None
            ),
            "denominator": "gamma_tradable_markets",
            "scope": "latest_collected_gamma_slice",
        },
        "freshness": {
            "latest_snapshot_bucket": snapshot_bucket,
            "resolution_watch_updated_at": (
                watch["latest_updated_at"]
                if watch
                else None
            ),
            "resolution_last_chain_checked_at": (
                watch["latest_chain_checked_at"]
                if watch
                else None
            ),
            "resolution_last_chain_checked_block": (
                watch["latest_chain_checked_block"]
                if watch
                else None
            ),
        },
        "resolution_truth": {
            "watch_rows": (
                watch["total"]
                if watch
                else 0
            ),
            "identity_ready": (
                watch["identity_ready"]
                if watch
                else 0
            ),
            "chain_unresolved": (
                watch["chain_unresolved"]
                if watch
                else 0
            ),
            "chain_resolved": (
                watch["chain_resolved"]
                if watch
                else 0
            ),
            "immutable_records": (
                resolutions["total"]
                if resolutions
                else 0
            ),
            "latest_observed_resolved_at": (
                resolutions[
                    "latest_observed_resolved_at"
                ]
                if resolutions
                else None
            ),
            "latest_valid_resolution_time": (
                resolutions[
                    "latest_valid_resolution_time"
                ]
                if resolutions
                else None
            ),
        },
        "authority": {
            "market_measurements": "snapshots",
            "execution_measurements": "clob_books",
            "forward_outcomes": "forward_outcomes",
            "resolution_tracking": "resolution_watch",
            "settlement_truth": "market_resolutions",
        },
        "capabilities": {
            "read_only": True,
            "signals": False,
            "brain": False,
            "execution": False,
            "capital_allocation": False,
            "event_measurements_exposed": False,
        },
    }


@app.get("/api/resolution-status/{market_id}")
def resolution_status(market_id: str):
    with connect() as conn:
        row = conn.execute("""
            SELECT *
            FROM resolution_watch
            WHERE market_id = ?
            LIMIT 1
        """, (market_id,)).fetchone()

        if row is None:
            raise HTTPException(
                status_code=404,
                detail="resolution_watch_not_found",
            )

        immutable = bool(
            conn.execute("""
                SELECT 1
                FROM market_resolutions
                WHERE market_id = ?
                LIMIT 1
            """, (market_id,)).fetchone()
        )

    return {
        "source_scope": resolution_scope(),
        "immutable_resolution_available": immutable,
        "resolution_status": resolution_watch_record(
            row
        ),
    }


@app.get("/api/resolution/{market_id}")
def resolution(market_id: str):
    with connect() as conn:
        row = conn.execute("""
            SELECT *
            FROM market_resolutions
            WHERE market_id = ?
            LIMIT 1
        """, (market_id,)).fetchone()

    if row is None:
        raise HTTPException(
            status_code=404,
            detail="market_not_resolved",
        )

    return {
        "source_scope": resolution_scope(),
        "resolution": resolution_record(row),
    }


@app.get("/api/resolutions")
def resolutions(
    limit: int = Query(100, ge=1, le=2000),
    offset: int = Query(0, ge=0),
    resolution_time_valid: bool | None = Query(None),
    evidence_status: str | None = Query(None),
):
    conditions = []
    params = []

    if resolution_time_valid is not None:
        conditions.append(
            "resolution_time_valid = ?"
        )
        params.append(int(resolution_time_valid))

    if evidence_status is not None:
        conditions.append(
            "resolution_evidence_status = ?"
        )
        params.append(evidence_status)

    where = (
        "WHERE " + " AND ".join(conditions)
        if conditions
        else ""
    )

    with connect() as conn:
        total = conn.execute(
            f"""
            SELECT COUNT(*)
            FROM market_resolutions
            {where}
            """,
            params,
        ).fetchone()[0]

        rows = conn.execute(
            f"""
            SELECT *
            FROM market_resolutions
            {where}
            ORDER BY
                COALESCE(
                    resolution_time,
                    first_observed_resolved_at
                ) DESC,
                market_id ASC
            LIMIT ? OFFSET ?
            """,
            [*params, limit, offset],
        ).fetchall()

    return {
        "total_matching": total,
        "limit": limit,
        "offset": offset,
        "source_scope": resolution_scope(),
        "rows": [
            resolution_record(row)
            for row in rows
        ],
    }


if __name__ == "__main__":
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8011,
        access_log=False,
        reload=False,
    )
