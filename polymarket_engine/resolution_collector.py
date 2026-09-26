import argparse
import fcntl
import json
import sqlite3
import time
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen


DB = Path("analytics/market_measurements.sqlite3")
LOCK = Path("/run/signalatlas_resolution_collector.lock")

GAMMA_MARKETS = "https://gamma-api.polymarket.com/markets"
RPC_URL = "https://polygon-bor-rpc.publicnode.com"

CHAIN_ID = 137

# Polymarket Conditional Tokens contract on Polygon.
CTF = "0x4D97DCd97eC945f40cF65F87097ACe5EA0476045"

# payoutDenominator(bytes32)
PAYOUT_DENOMINATOR_SELECTOR = "dd34de67"

# payoutNumerators(bytes32,uint256)
PAYOUT_NUMERATOR_SELECTOR = "0504c814"

# ConditionResolution(bytes32,address,bytes32,uint256,uint256[])
CONDITION_RESOLUTION_TOPIC = (
    "0xb44d84d3289691f71497564b85d4233648d9dbae8cbdbb4329f301c3a0185894"
)

# PublicNode allows at most 10,000 blocks per eth_getLogs call.
LOG_BLOCK_CHUNK = 9000

SCHEMA_VERSION = "canonical_resolution_v1"
USER_AGENT = "SignalAtlas-ResolutionCollector/1.0"

REQUEST_TIMEOUT = 15
REQUEST_RETRIES = 3
REQUEST_PAUSE_S = 0.04


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def json_compact(value):
    return json.dumps(
        value,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def parse_json_list(value):
    if isinstance(value, list):
        return value

    if isinstance(value, str):
        try:
            x = json.loads(value)
            return x if isinstance(x, list) else []
        except Exception:
            return []

    return []


def clean_condition_id(value):
    if value is None:
        return None

    x = str(value).strip().lower()

    if x.startswith("0x"):
        x = x[2:]

    if len(x) != 64:
        return None

    try:
        int(x, 16)
    except Exception:
        return None

    return "0x" + x


def http_json(url, payload=None):
    last = None

    for attempt in range(REQUEST_RETRIES):
        try:
            headers = {
                "User-Agent": USER_AGENT,
                "Accept": "application/json",
            }

            data = None

            if payload is not None:
                data = json.dumps(payload).encode("utf-8")
                headers["Content-Type"] = "application/json"

            req = Request(
                url,
                data=data,
                headers=headers,
            )

            with urlopen(
                req,
                timeout=REQUEST_TIMEOUT,
            ) as response:
                return json.loads(
                    response.read().decode("utf-8")
                )

        except Exception as exc:
            last = exc

            if attempt + 1 < REQUEST_RETRIES:
                time.sleep(0.4 * (attempt + 1))

    raise last


def rpc(method, params):
    response = http_json(
        RPC_URL,
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params,
        },
    )

    if not isinstance(response, dict):
        raise RuntimeError("rpc_non_object_response")

    if response.get("error") is not None:
        raise RuntimeError(
            f"rpc_error:{response['error']}"
        )

    if "result" not in response:
        raise RuntimeError("rpc_result_missing")

    return response["result"]


def eth_call(calldata):
    result = rpc(
        "eth_call",
        [
            {
                "to": CTF,
                "data": calldata,
            },
            "latest",
        ],
    )

    return int(result, 16)


def payout_denominator(condition_id):
    c = condition_id.removeprefix("0x")

    return eth_call(
        "0x"
        + PAYOUT_DENOMINATOR_SELECTOR
        + c
    )


def payout_numerator(condition_id, index):
    c = condition_id.removeprefix("0x")
    encoded_index = hex(index)[2:].rjust(64, "0")

    return eth_call(
        "0x"
        + PAYOUT_NUMERATOR_SELECTOR
        + c
        + encoded_index
    )


def current_block_number():
    return int(
        rpc("eth_blockNumber", []),
        16,
    )


def block_time_iso(block_number):
    block = rpc(
        "eth_getBlockByNumber",
        [hex(block_number), False],
    )

    if not block:
        raise RuntimeError(
            "resolution_block_not_found"
        )

    ts = int(block["timestamp"], 16)

    return datetime.fromtimestamp(
        ts,
        timezone.utc,
    ).isoformat()


def find_resolution_event(
    condition_id,
    from_block,
    to_block,
):
    if from_block is None:
        return None

    if to_block < from_block:
        return None

    matches = []

    start = max(0, int(from_block))
    end = int(to_block)

    while start <= end:
        chunk_end = min(
            end,
            start + LOG_BLOCK_CHUNK - 1,
        )

        logs = rpc(
            "eth_getLogs",
            [{
                "address": CTF,
                "fromBlock": hex(start),
                "toBlock": hex(chunk_end),
                "topics": [
                    CONDITION_RESOLUTION_TOPIC,
                    condition_id,
                ],
            }],
        )

        if logs:
            matches.extend(logs)

        start = chunk_end + 1

    if len(matches) == 0:
        return None

    if len(matches) != 1:
        raise RuntimeError(
            f"unexpected_resolution_event_count:{len(matches)}"
        )

    log = matches[0]
    block_number = int(
        log["blockNumber"],
        16,
    )

    return {
        "resolution_block": block_number,
        "resolution_time":
            block_time_iso(block_number),
        "resolution_tx_hash":
            log["transactionHash"],
        "resolution_log_index":
            int(log["logIndex"], 16),
    }


def fetch_gamma_identity(market_id):
    url = (
        GAMMA_MARKETS
        + "/"
        + urllib.parse.quote(
            str(market_id),
            safe="",
        )
    )

    raw = http_json(url)

    if not isinstance(raw, dict):
        raise RuntimeError("gamma_market_non_object")

    condition_id = clean_condition_id(
        raw.get("conditionId")
        or raw.get("condition_id")
    )

    outcomes = parse_json_list(
        raw.get("outcomes")
    )

    market_name = (
        raw.get("question")
        or raw.get("title")
        or raw.get("slug")
        or f"Market {market_id}"
    )

    if condition_id is None:
        raise RuntimeError(
            "gamma_condition_id_missing_or_invalid"
        )

    if len(outcomes) < 2:
        raise RuntimeError(
            "gamma_outcomes_missing_or_invalid"
        )

    return {
        "market_id": str(market_id),
        "market_name": market_name,
        "condition_id": condition_id,
        "outcomes": outcomes,
    }


def init_db(conn):
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA busy_timeout=5000")

    conn.execute("""
        CREATE TABLE IF NOT EXISTS resolution_watch (
            market_id TEXT PRIMARY KEY,

            market_name TEXT,

            first_observed_at TEXT NOT NULL,
            last_snapshot_at TEXT NOT NULL,

            latest_active INTEGER,
            latest_closed INTEGER,

            condition_id TEXT,
            outcomes_json TEXT,

            identity_status TEXT NOT NULL,
            identity_source TEXT,
            last_identity_checked_at TEXT,

            chain_status TEXT NOT NULL,
            last_chain_checked_at TEXT,
            last_chain_checked_block INTEGER,

            last_error TEXT,

            schema_version TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE INDEX IF NOT EXISTS
        idx_resolution_watch_condition
        ON resolution_watch (condition_id)
    """)

    conn.execute("""
        CREATE INDEX IF NOT EXISTS
        idx_resolution_watch_chain_status
        ON resolution_watch (
            chain_status,
            last_chain_checked_at
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS market_resolutions (
            market_id TEXT PRIMARY KEY,

            condition_id TEXT NOT NULL,
            market_name TEXT,

            outcomes_json TEXT NOT NULL,

            payout_denominator_raw TEXT NOT NULL,
            payout_numerators_json TEXT NOT NULL,
            normalized_payouts_json TEXT NOT NULL,

            positive_payout_indices_json TEXT NOT NULL,
            positive_payout_labels_json TEXT NOT NULL,

            first_observed_resolved_at TEXT NOT NULL,

            resolution_time TEXT,
            resolution_time_valid INTEGER NOT NULL,
            resolution_time_source TEXT,

            resolution_block INTEGER,
            resolution_tx_hash TEXT,
            resolution_log_index INTEGER,
            resolution_evidence_status TEXT NOT NULL,

            source_chain_id INTEGER NOT NULL,
            source_contract TEXT NOT NULL,
            source_method TEXT NOT NULL,

            schema_version TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE INDEX IF NOT EXISTS
        idx_market_resolutions_condition
        ON market_resolutions (condition_id)
    """)

    watch_columns = {
        row[1]
        for row in conn.execute(
            "PRAGMA table_info(resolution_watch)"
        )
    }

    if "last_chain_checked_block" not in watch_columns:
        conn.execute("""
            ALTER TABLE resolution_watch
            ADD COLUMN last_chain_checked_block INTEGER
        """)

    resolution_columns = {
        row[1]
        for row in conn.execute(
            "PRAGMA table_info(market_resolutions)"
        )
    }

    migrations = {
        "resolution_time":
            "ALTER TABLE market_resolutions ADD COLUMN resolution_time TEXT",
        "resolution_time_valid":
            "ALTER TABLE market_resolutions ADD COLUMN resolution_time_valid INTEGER",
        "resolution_time_source":
            "ALTER TABLE market_resolutions ADD COLUMN resolution_time_source TEXT",
        "resolution_block":
            "ALTER TABLE market_resolutions ADD COLUMN resolution_block INTEGER",
        "resolution_tx_hash":
            "ALTER TABLE market_resolutions ADD COLUMN resolution_tx_hash TEXT",
        "resolution_log_index":
            "ALTER TABLE market_resolutions ADD COLUMN resolution_log_index INTEGER",
        "resolution_evidence_status":
            "ALTER TABLE market_resolutions ADD COLUMN resolution_evidence_status TEXT",
    }

    for column, sql in migrations.items():
        if column not in resolution_columns:
            conn.execute(sql)


def sync_observed_markets(conn):
    rows = conn.execute("""
        WITH bounds AS (
            SELECT
                market_id,
                MIN(observed_at) AS first_observed_at,
                MAX(observation_bucket) AS last_bucket
            FROM snapshots
            GROUP BY market_id
        )
        SELECT
            s.market_id,
            s.market_name,
            b.first_observed_at,
            s.observed_at AS last_snapshot_at,
            s.active,
            s.closed
        FROM bounds b
        JOIN snapshots s
          ON s.market_id = b.market_id
         AND s.observation_bucket = b.last_bucket
        ORDER BY s.market_id
    """).fetchall()

    ts = now_iso()

    for row in rows:
        conn.execute("""
            INSERT INTO resolution_watch (
                market_id,
                market_name,
                first_observed_at,
                last_snapshot_at,
                latest_active,
                latest_closed,
                condition_id,
                outcomes_json,
                identity_status,
                identity_source,
                last_identity_checked_at,
                chain_status,
                last_chain_checked_at,
                last_chain_checked_block,
                last_error,
                schema_version,
                updated_at
            )
            VALUES (
                ?, ?, ?, ?, ?, ?,
                NULL, NULL,
                'PENDING',
                NULL,
                NULL,
                'UNCHECKED',
                NULL,
                NULL,
                NULL,
                ?,
                ?
            )
            ON CONFLICT(market_id) DO UPDATE SET
                market_name = COALESCE(
                    excluded.market_name,
                    resolution_watch.market_name
                ),
                last_snapshot_at =
                    excluded.last_snapshot_at,
                latest_active =
                    excluded.latest_active,
                latest_closed =
                    excluded.latest_closed,
                updated_at =
                    excluded.updated_at
        """, (
            str(row["market_id"]),
            row["market_name"],
            row["first_observed_at"],
            row["last_snapshot_at"],
            row["active"],
            row["closed"],
            SCHEMA_VERSION,
            ts,
        ))

    conn.commit()

    return len(rows)


def populate_identity(conn, limit):
    rows = conn.execute("""
        SELECT
            market_id
        FROM resolution_watch
        WHERE condition_id IS NULL
          AND identity_status != 'NO_CONDITION'
        ORDER BY
            CASE
                WHEN last_identity_checked_at IS NULL
                THEN 0 ELSE 1
            END,
            last_identity_checked_at ASC,
            market_id ASC
        LIMIT ?
    """, (limit,)).fetchall()

    ready = 0
    no_condition = 0
    errors = 0

    for row in rows:
        market_id = str(row["market_id"])
        ts = now_iso()

        try:
            identity = fetch_gamma_identity(
                market_id
            )

            conn.execute("""
                UPDATE resolution_watch
                SET
                    market_name = ?,
                    condition_id = ?,
                    outcomes_json = ?,
                    identity_status = 'READY',
                    identity_source =
                        'Polymarket Gamma API',
                    last_identity_checked_at = ?,
                    last_error = NULL,
                    updated_at = ?
                WHERE market_id = ?
            """, (
                identity["market_name"],
                identity["condition_id"],
                json_compact(
                    identity["outcomes"]
                ),
                ts,
                ts,
                market_id,
            ))

            conn.commit()
            ready += 1

        except Exception as exc:
            if (
                isinstance(exc, RuntimeError)
                and str(exc) == "gamma_condition_id_missing_or_invalid"
            ):
                conn.execute("""
                    UPDATE resolution_watch
                    SET
                        identity_status = 'NO_CONDITION',
                        identity_source = 'Polymarket Gamma API',
                        last_identity_checked_at = ?,
                        last_error = NULL,
                        updated_at = ?
                    WHERE market_id = ?
                """, (
                    ts,
                    ts,
                    market_id,
                ))

                conn.commit()
                no_condition += 1

            else:
                conn.execute("""
                    UPDATE resolution_watch
                    SET
                        identity_status = 'ERROR',
                        last_identity_checked_at = ?,
                        last_error = ?,
                        updated_at = ?
                    WHERE market_id = ?
                """, (
                    ts,
                    f"{type(exc).__name__}:{exc}"[:500],
                    ts,
                    market_id,
                ))

                conn.commit()
                errors += 1

        time.sleep(REQUEST_PAUSE_S)

    return {
        "attempted": len(rows),
        "ready": ready,
        "no_condition": no_condition,
        "errors": errors,
    }


def verify_or_insert_resolution(
    conn,
    row,
    denominator,
    numerators,
    evidence,
):
    market_id = str(row["market_id"])
    condition_id = row["condition_id"]

    outcomes = parse_json_list(
        row["outcomes_json"]
    )

    if len(outcomes) != len(numerators):
        raise RuntimeError(
            "outcome_payout_length_mismatch"
        )

    if denominator <= 0:
        raise RuntimeError(
            "invalid_nonpositive_denominator"
        )

    if sum(numerators) != denominator:
        raise RuntimeError(
            "payout_vector_sum_mismatch"
        )

    normalized = [
        n / denominator
        for n in numerators
    ]

    positive_indices = [
        i
        for i, n in enumerate(numerators)
        if n > 0
    ]

    positive_labels = [
        outcomes[i]
        for i in positive_indices
    ]

    existing = conn.execute("""
        SELECT
            condition_id,
            payout_denominator_raw,
            payout_numerators_json
        FROM market_resolutions
        WHERE market_id = ?
    """, (market_id,)).fetchone()

    if existing is not None:
        same = (
            existing["condition_id"]
            == condition_id
            and existing["payout_denominator_raw"]
            == str(denominator)
            and json.loads(
                existing["payout_numerators_json"]
            ) == numerators
        )

        if not same:
            raise RuntimeError(
                "immutable_resolution_conflict"
            )

        return False

    conn.execute("""
        INSERT INTO market_resolutions (
            market_id,
            condition_id,
            market_name,
            outcomes_json,
            payout_denominator_raw,
            payout_numerators_json,
            normalized_payouts_json,
            positive_payout_indices_json,
            positive_payout_labels_json,
            first_observed_resolved_at,

            resolution_time,
            resolution_time_valid,
            resolution_time_source,

            resolution_block,
            resolution_tx_hash,
            resolution_log_index,
            resolution_evidence_status,

            source_chain_id,
            source_contract,
            source_method,
            schema_version
        )
        VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
            ?, ?, ?,
            ?, ?, ?, ?,
            ?, ?, ?, ?
        )
    """, (
        market_id,
        condition_id,
        row["market_name"],
        json_compact(outcomes),
        str(denominator),
        json_compact(numerators),
        json_compact(normalized),
        json_compact(positive_indices),
        json_compact(positive_labels),
        now_iso(),

        evidence.get("resolution_time")
            if evidence else None,
        1 if evidence else 0,
        (
            "Polygon CTF ConditionResolution event"
            if evidence else None
        ),

        evidence.get("resolution_block")
            if evidence else None,
        evidence.get("resolution_tx_hash")
            if evidence else None,
        evidence.get("resolution_log_index")
            if evidence else None,
        (
            "CHAIN_EVENT"
            if evidence
            else "FIRST_OBSERVED_ONLY"
        ),

        CHAIN_ID,
        CTF,
        "CTF payoutDenominator + payoutNumerators",
        SCHEMA_VERSION,
    ))

    return True


def collect_chain_truth(conn, limit):
    rows = conn.execute("""
        WITH latest_snapshot AS (
            SELECT
                s.market_id,
                s.raw_resolution_time
            FROM snapshots s
            JOIN (
                SELECT
                    market_id,
                    MAX(observation_bucket) AS observation_bucket
                FROM snapshots
                GROUP BY market_id
            ) x
              ON x.market_id = s.market_id
             AND x.observation_bucket = s.observation_bucket
        )
        SELECT
            w.market_id,
            w.market_name,
            w.condition_id,
            w.outcomes_json,
            w.latest_closed,
            w.last_chain_checked_at,
            w.last_chain_checked_block,
            ls.raw_resolution_time
        FROM resolution_watch w
        LEFT JOIN latest_snapshot ls
          ON ls.market_id = w.market_id
        WHERE
            w.condition_id IS NOT NULL
            AND w.identity_status = 'READY'
            AND w.chain_status != 'RESOLVED'
            AND (
                -- Every condition must first receive a prospective
                -- unresolved block anchor.
                w.last_chain_checked_at IS NULL
                OR w.last_chain_checked_block IS NULL

                -- Transient chain errors retry independently of
                -- market-lifecycle scheduling.
                OR (
                    w.chain_status = 'ERROR'
                    AND datetime(w.last_chain_checked_at)
                        <= datetime('now', '-1 hour')
                )

                -- raw_resolution_time is a polling hint only.
                -- Polygon CTF remains settlement authority.
                OR (
                    ls.raw_resolution_time IS NOT NULL
                    AND datetime(ls.raw_resolution_time)
                        <= datetime('now')
                    AND datetime(w.last_chain_checked_at)
                        <= datetime('now', '-15 minutes')
                )

                OR (
                    ls.raw_resolution_time IS NOT NULL
                    AND datetime(ls.raw_resolution_time)
                        > datetime('now')
                    AND datetime(ls.raw_resolution_time)
                        <= datetime('now', '+7 days')
                    AND datetime(w.last_chain_checked_at)
                        <= datetime('now', '-6 hours')
                )

                OR (
                    ls.raw_resolution_time IS NOT NULL
                    AND datetime(ls.raw_resolution_time)
                        > datetime('now', '+7 days')
                    AND datetime(ls.raw_resolution_time)
                        <= datetime('now', '+90 days')
                    AND datetime(w.last_chain_checked_at)
                        <= datetime('now', '-24 hours')
                )

                OR (
                    ls.raw_resolution_time IS NOT NULL
                    AND datetime(ls.raw_resolution_time)
                        > datetime('now', '+90 days')
                    AND datetime(w.last_chain_checked_at)
                        <= datetime('now', '-7 days')
                )

                OR (
                    ls.raw_resolution_time IS NULL
                    AND datetime(w.last_chain_checked_at)
                        <= datetime('now', '-24 hours')
                )
            )
        ORDER BY
            -- Bootstrap prospective block anchors first.
            CASE
                WHEN w.last_chain_checked_block IS NULL
                THEN 0 ELSE 1
            END,

            -- Then retry actual errors.
            CASE
                WHEN w.chain_status = 'ERROR'
                THEN 0 ELSE 1
            END,

            -- Then lifecycle urgency.
            CASE
                WHEN ls.raw_resolution_time IS NOT NULL
                 AND datetime(ls.raw_resolution_time)
                    <= datetime('now')
                THEN 0

                WHEN ls.raw_resolution_time IS NOT NULL
                 AND datetime(ls.raw_resolution_time)
                    <= datetime('now', '+7 days')
                THEN 1

                WHEN ls.raw_resolution_time IS NOT NULL
                 AND datetime(ls.raw_resolution_time)
                    <= datetime('now', '+90 days')
                THEN 2

                WHEN ls.raw_resolution_time IS NULL
                THEN 3

                ELSE 4
            END,

            w.last_chain_checked_at ASC,
            datetime(ls.raw_resolution_time) ASC,
            w.market_id ASC
        LIMIT ?
    """, (limit,)).fetchall()

    checked = 0
    unresolved = 0
    newly_resolved = 0
    errors = 0

    cycle_block = (
        current_block_number()
        if rows else None
    )

    for row in rows:
        market_id = str(row["market_id"])
        condition_id = row["condition_id"]
        ts = now_iso()

        try:
            denominator = payout_denominator(
                condition_id
            )

            checked += 1

            if denominator == 0:
                conn.execute("""
                    UPDATE resolution_watch
                    SET
                        chain_status = 'UNRESOLVED',
                        last_chain_checked_at = ?,
                        last_chain_checked_block = ?,
                        last_error = NULL,
                        updated_at = ?
                    WHERE market_id = ?
                """, (
                    ts,
                    cycle_block,
                    ts,
                    market_id,
                ))

                conn.commit()
                unresolved += 1

                time.sleep(REQUEST_PAUSE_S)
                continue

            outcomes = parse_json_list(
                row["outcomes_json"]
            )

            if len(outcomes) < 2:
                raise RuntimeError(
                    "outcomes_missing_for_resolved_condition"
                )

            numerators = []

            for index in range(len(outcomes)):
                numerators.append(
                    payout_numerator(
                        condition_id,
                        index,
                    )
                )

                time.sleep(REQUEST_PAUSE_S)

            previous_block = (
                row["last_chain_checked_block"]
            )

            evidence = None

            if previous_block is not None:
                evidence = find_resolution_event(
                    condition_id,
                    int(previous_block) + 1,
                    cycle_block,
                )

                if evidence is None:
                    raise RuntimeError(
                        "resolved_but_condition_event_missing"
                    )

            inserted = verify_or_insert_resolution(
                conn,
                row,
                denominator,
                numerators,
                evidence,
            )

            conn.execute("""
                UPDATE resolution_watch
                SET
                    chain_status = 'RESOLVED',
                    last_chain_checked_at = ?,
                    last_chain_checked_block = ?,
                    last_error = NULL,
                    updated_at = ?
                WHERE market_id = ?
            """, (
                ts,
                cycle_block,
                ts,
                market_id,
            ))

            conn.commit()

            if inserted:
                newly_resolved += 1

        except Exception as exc:
            conn.execute("""
                UPDATE resolution_watch
                SET
                    chain_status = 'ERROR',
                    last_chain_checked_at = ?,
                    last_error = ?,
                    updated_at = ?
                WHERE market_id = ?
            """, (
                ts,
                f"{type(exc).__name__}:{exc}"[:500],
                ts,
                market_id,
            ))

            conn.commit()
            errors += 1

        time.sleep(REQUEST_PAUSE_S)

    return {
        "selected": len(rows),
        "checked": checked,
        "unresolved": unresolved,
        "newly_resolved": newly_resolved,
        "errors": errors,
    }


def summary(conn):
    watch = conn.execute("""
        SELECT
            COUNT(*) AS total,
            SUM(condition_id IS NOT NULL) AS identity_ready,
            SUM(identity_status = 'ERROR') AS identity_error,
            SUM(chain_status = 'UNRESOLVED') AS unresolved,
            SUM(chain_status = 'RESOLVED') AS resolved,
            SUM(chain_status = 'ERROR') AS chain_error
        FROM resolution_watch
    """).fetchone()

    resolutions = conn.execute("""
        SELECT COUNT(*) AS n
        FROM market_resolutions
    """).fetchone()["n"]

    return {
        "watch_total": watch["total"] or 0,
        "identity_ready":
            watch["identity_ready"] or 0,
        "identity_error":
            watch["identity_error"] or 0,
        "chain_unresolved":
            watch["unresolved"] or 0,
        "chain_resolved":
            watch["resolved"] or 0,
        "chain_error":
            watch["chain_error"] or 0,
        "immutable_resolutions":
            resolutions or 0,
    }


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--identity-limit",
        type=int,
        default=100,
    )

    parser.add_argument(
        "--chain-limit",
        type=int,
        default=250,
    )

    args = parser.parse_args()

    if args.identity_limit < 0:
        raise SystemExit(
            "identity_limit_must_be_nonnegative"
        )

    if args.chain_limit < 0:
        raise SystemExit(
            "chain_limit_must_be_nonnegative"
        )

    LOCK.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    lock_handle = LOCK.open("w")

    try:
        fcntl.flock(
            lock_handle,
            fcntl.LOCK_EX | fcntl.LOCK_NB,
        )
    except BlockingIOError:
        raise SystemExit(
            "RESOLUTION_COLLECTOR_ALREADY_RUNNING"
        )

    chain_id = int(
        rpc("eth_chainId", []),
        16,
    )

    if chain_id != CHAIN_ID:
        raise SystemExit(
            f"WRONG_CHAIN_ID:{chain_id}"
        )

    conn = sqlite3.connect(
        DB,
        timeout=10,
    )
    conn.row_factory = sqlite3.Row

    try:
        init_db(conn)
        conn.commit()

        observed = sync_observed_markets(
            conn
        )

        identity_result = populate_identity(
            conn,
            args.identity_limit,
        )

        chain_result = collect_chain_truth(
            conn,
            args.chain_limit,
        )

        final = summary(conn)

        print(
            "RESOLUTION_COLLECTION_OK"
        )
        print(
            f"chain_id={chain_id}"
        )
        print(
            f"observed_markets={observed}"
        )
        print(
            "identity "
            f"attempted={identity_result['attempted']} "
            f"ready={identity_result['ready']} "
            f"no_condition={identity_result['no_condition']} "
            f"errors={identity_result['errors']}"
        )
        print(
            "chain "
            f"selected={chain_result['selected']} "
            f"checked={chain_result['checked']} "
            f"unresolved={chain_result['unresolved']} "
            f"newly_resolved={chain_result['newly_resolved']} "
            f"errors={chain_result['errors']}"
        )
        print(
            "state "
            f"watch={final['watch_total']} "
            f"identity_ready={final['identity_ready']} "
            f"identity_error={final['identity_error']} "
            f"chain_unresolved={final['chain_unresolved']} "
            f"chain_resolved={final['chain_resolved']} "
            f"chain_error={final['chain_error']} "
            f"immutable_resolutions={final['immutable_resolutions']}"
        )

    finally:
        conn.close()
        lock_handle.close()


if __name__ == "__main__":
    main()
