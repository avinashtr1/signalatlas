import json
import time
import uuid
import fcntl
import sqlite3
from pathlib import Path
from datetime import datetime, timezone

from py_clob_client.client import ClobClient
from py_clob_client.clob_types import BookParams


RAW = Path("analytics/market_raw.json")
OUT = Path("analytics/orderbooks.json")
DB = Path("analytics/market_measurements.sqlite3")
LOCK = Path("/run/signalatlas_orderbook_collector.lock")

HOST = "https://clob.polymarket.com"
BATCH_SIZE = 100
VWAP_NOTIONALS = (10, 50, 100)
DEPTH_WINDOWS = (0.01, 0.02, 0.05)


def getv(obj, key):
    if isinstance(obj, dict):
        return obj.get(key)
    return getattr(obj, key, None)


def book_token(book):
    for key in ("asset_id", "token_id"):
        v = getv(book, key)
        if v is not None:
            return str(v)
    return None


def parse_levels(levels):
    out = []

    for level in levels or []:
        try:
            price = float(getv(level, "price"))
            size = float(getv(level, "size"))

            if 0 < price < 1 and size > 0:
                out.append((price, size))
        except Exception:
            continue

    return out


def execution_vwap(levels, target_usd, ascending):
    ordered = sorted(
        levels,
        key=lambda x: x[0],
        reverse=not ascending,
    )

    dollars = 0.0
    shares = 0.0

    for price, size in ordered:
        capacity = price * size
        take = min(target_usd - dollars, capacity)

        if take <= 0:
            break

        dollars += take
        shares += take / price

        if dollars >= target_usd - 1e-9:
            break

    fill_ratio = (
        min(1.0, dollars / target_usd)
        if target_usd > 0 else 0.0
    )

    vwap = dollars / shares if shares > 0 else None

    return vwap, fill_ratio


def summarize_book(book):
    bids = parse_levels(getv(book, "bids") or [])
    asks = parse_levels(getv(book, "asks") or [])

    best_bid = max((p for p, _ in bids), default=None)
    best_ask = min((p for p, _ in asks), default=None)

    if best_bid is not None and best_ask is not None:
        quote_state = "TWO_SIDED"
        spread = best_ask - best_bid
    elif best_bid is not None or best_ask is not None:
        quote_state = "ONE_SIDED"
        spread = None
    else:
        quote_state = "NO_BOOK"
        spread = None

    top_bid_size = (
        sum(s for p, s in bids if abs(p - best_bid) < 1e-12)
        if best_bid is not None else None
    )

    top_ask_size = (
        sum(s for p, s in asks if abs(p - best_ask) < 1e-12)
        if best_ask is not None else None
    )

    result = {
        "quote_state": quote_state,
        "best_bid": best_bid,
        "best_ask": best_ask,
        "spread": spread,

        "bid_levels": len(bids),
        "ask_levels": len(asks),

        "top_bid_size": top_bid_size,
        "top_ask_size": top_ask_size,

        "total_bid_shares": sum(s for _, s in bids),
        "total_ask_shares": sum(s for _, s in asks),

        "total_bid_notional_usd":
            sum(p * s for p, s in bids),

        "total_ask_notional_usd":
            sum(p * s for p, s in asks),
    }

    for window in DEPTH_WINDOWS:
        cents = int(round(window * 100))

        bid_depth = (
            sum(
                p * s
                for p, s in bids
                if best_bid is not None
                and p >= best_bid - window - 1e-12
            )
        )

        ask_depth = (
            sum(
                p * s
                for p, s in asks
                if best_ask is not None
                and p <= best_ask + window + 1e-12
            )
        )

        result[f"bid_depth_{cents}c_usd"] = bid_depth
        result[f"ask_depth_{cents}c_usd"] = ask_depth

    for notional in VWAP_NOTIONALS:
        buy_vwap, buy_fill = execution_vwap(
            asks,
            notional,
            ascending=True,
        )

        sell_vwap, sell_fill = execution_vwap(
            bids,
            notional,
            ascending=False,
        )

        result[f"buy_vwap_{notional}"] = buy_vwap
        result[f"buy_fill_{notional}"] = buy_fill

        result[f"sell_vwap_{notional}"] = sell_vwap
        result[f"sell_fill_{notional}"] = sell_fill

    return result


def init_db(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS clob_books (
            market_id TEXT NOT NULL,
            market_name TEXT,
            token_id TEXT NOT NULL,
            outcome_side TEXT NOT NULL,

            observation_bucket TEXT NOT NULL,
            observed_at TEXT NOT NULL,

            collection_status TEXT NOT NULL,
            quote_state TEXT,

            best_bid REAL,
            best_ask REAL,
            spread REAL,

            bid_levels INTEGER,
            ask_levels INTEGER,

            top_bid_size REAL,
            top_ask_size REAL,

            total_bid_shares REAL,
            total_ask_shares REAL,
            total_bid_notional_usd REAL,
            total_ask_notional_usd REAL,

            bid_depth_1c_usd REAL,
            ask_depth_1c_usd REAL,
            bid_depth_2c_usd REAL,
            ask_depth_2c_usd REAL,
            bid_depth_5c_usd REAL,
            ask_depth_5c_usd REAL,

            buy_vwap_10 REAL,
            buy_fill_10 REAL,
            buy_vwap_50 REAL,
            buy_fill_50 REAL,
            buy_vwap_100 REAL,
            buy_fill_100 REAL,

            sell_vwap_10 REAL,
            sell_fill_10 REAL,
            sell_vwap_50 REAL,
            sell_fill_50 REAL,
            sell_vwap_100 REAL,
            sell_fill_100 REAL,

            PRIMARY KEY (
                token_id,
                observation_bucket
            )
        )
    """)

    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_clob_market_bucket
        ON clob_books (
            market_id,
            observation_bucket
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS clob_collection_runs (
            run_id TEXT PRIMARY KEY,
            observation_bucket TEXT NOT NULL,
            started_at TEXT NOT NULL,
            completed_at TEXT NOT NULL,

            markets_requested INTEGER NOT NULL,
            tokens_requested INTEGER NOT NULL,
            books_returned INTEGER NOT NULL,

            batch_failures INTEGER NOT NULL,
            missing_tokens INTEGER NOT NULL,

            status TEXT NOT NULL,
            latency_ms REAL NOT NULL
        )
    """)


def init_event_measurements_db(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS event_measurements (
            event_id TEXT NOT NULL,
            event_title TEXT,

            observation_bucket TEXT NOT NULL,
            observed_at TEXT NOT NULL,

            schema_version TEXT NOT NULL,
            source_scope_complete_universe INTEGER NOT NULL,
            clob_run_status TEXT NOT NULL,

            market_count INTEGER NOT NULL,
            two_sided_count INTEGER NOT NULL,
            two_sided_fraction REAL NOT NULL,

            priced_market_count INTEGER NOT NULL,
            mid_q25 REAL,
            mid_median REAL,
            mid_q75 REAL,
            mid_iqr REAL,

            mid_40_60_count INTEGER NOT NULL,
            mid_40_60_fraction REAL NOT NULL,

            spread_count INTEGER NOT NULL,
            median_spread REAL,

            spread_0p001_0p0025_count INTEGER NOT NULL,
            spread_0p001_0p0025_fraction REAL NOT NULL,

            liquidity_count INTEGER NOT NULL,
            total_liquidity_usd REAL,
            median_liquidity_usd REAL,

            volume_count INTEGER NOT NULL,
            total_volume_usd REAL,
            median_volume_usd REAL,

            clob_market_count INTEGER NOT NULL,
            clob_coverage_fraction REAL NOT NULL,

            clob_depth_2c_market_count INTEGER NOT NULL,
            median_clob_depth_2c_usd REAL,

            clob_total_book_market_count INTEGER NOT NULL,
            median_clob_total_book_notional_usd REAL,

            clob_imbalance_side_count INTEGER NOT NULL,
            median_clob_abs_imbalance REAL,

            median_clob_spread REAL,

            delta_15m_two_sided_fraction REAL,
            delta_30m_two_sided_fraction REAL,

            delta_15m_mid_iqr REAL,
            delta_30m_mid_iqr REAL,

            delta_15m_spread_0p001_0p0025_fraction REAL,
            delta_30m_spread_0p001_0p0025_fraction REAL,

            delta_15m_median_spread REAL,
            delta_30m_median_spread REAL,

            delta_15m_total_liquidity_usd REAL,
            delta_30m_total_liquidity_usd REAL,

            delta_15m_median_clob_depth_2c_usd REAL,
            delta_30m_median_clob_depth_2c_usd REAL,

            delta_15m_median_clob_total_book_notional_usd REAL,
            delta_30m_median_clob_total_book_notional_usd REAL,

            delta_15m_median_clob_abs_imbalance REAL,
            delta_30m_median_clob_abs_imbalance REAL,

            delta_15m_median_clob_spread REAL,
            delta_30m_median_clob_spread REAL,

            PRIMARY KEY (
                event_id,
                observation_bucket
            )
        )
    """)

    existing_columns = {
        row[1]
        for row in conn.execute(
            "PRAGMA table_info(event_measurements)"
        ).fetchall()
    }

    for column in (
        "median_clob_spread",
        "delta_15m_median_clob_spread",
        "delta_30m_median_clob_spread",
    ):
        if column not in existing_columns:
            conn.execute(
                f"ALTER TABLE event_measurements "
                f"ADD COLUMN {column} REAL"
            )

    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_event_measurements_bucket
        ON event_measurements (
            observation_bucket
        )
    """)


def _event_median(values):
    xs = sorted(
        float(x)
        for x in values
        if x is not None
    )

    if not xs:
        return None

    n = len(xs)
    m = n // 2

    if n % 2:
        return xs[m]

    return (xs[m - 1] + xs[m]) / 2.0


def _event_quantile(values, q):
    xs = sorted(
        float(x)
        for x in values
        if x is not None
    )

    if not xs:
        return None

    if len(xs) == 1:
        return xs[0]

    pos = (len(xs) - 1) * q
    lo = int(pos)
    hi = min(lo + 1, len(xs) - 1)
    frac = pos - lo

    return (
        xs[lo] * (1.0 - frac)
        + xs[hi] * frac
    )


def _event_delta(current, previous):
    if current is None or previous is None:
        return None

    return float(current) - float(previous)


def write_event_measurements(
    conn,
    observation_bucket,
    observed_at,
    clob_run_status,
):
    from collections import defaultdict
    from datetime import datetime, timedelta

    snapshot_rows = conn.execute("""
        SELECT
            market_id,
            event_id,
            event_title,
            mid_price,
            spread,
            two_sided,
            volume_total_usd,
            liquidity_usd
        FROM snapshots
        WHERE observation_bucket = ?
          AND event_id IS NOT NULL
        ORDER BY event_id, market_id
    """, (
        observation_bucket,
    )).fetchall()

    events = defaultdict(list)

    for (
        market_id,
        event_id,
        event_title,
        mid_price,
        spread,
        two_sided,
        volume_total_usd,
        liquidity_usd,
    ) in snapshot_rows:
        events[str(event_id)].append({
            "market_id": str(market_id),
            "event_title": event_title,
            "mid_price": mid_price,
            "spread": spread,
            "two_sided": two_sided,
            "volume_total_usd": volume_total_usd,
            "liquidity_usd": liquidity_usd,
        })

    book_rows = conn.execute("""
        SELECT
            market_id,
            UPPER(outcome_side),
            quote_state,
            spread,
            bid_depth_2c_usd,
            ask_depth_2c_usd,
            total_bid_notional_usd,
            total_ask_notional_usd
        FROM clob_books
        WHERE observation_bucket = ?
          AND collection_status = 'OK'
    """, (
        observation_bucket,
    )).fetchall()

    books = defaultdict(dict)

    for (
        market_id,
        outcome_side,
        quote_state,
        spread,
        bid_depth_2c_usd,
        ask_depth_2c_usd,
        total_bid_notional_usd,
        total_ask_notional_usd,
    ) in book_rows:
        books[str(market_id)][outcome_side] = {
            "quote_state":
                quote_state,
            "spread":
                spread,
            "bid_depth_2c_usd":
                bid_depth_2c_usd,
            "ask_depth_2c_usd":
                ask_depth_2c_usd,
            "total_bid_notional_usd":
                total_bid_notional_usd,
            "total_ask_notional_usd":
                total_ask_notional_usd,
        }

    bucket_dt = datetime.fromisoformat(
        str(observation_bucket)
    )

    rows = []

    prior_columns = """
        two_sided_fraction,
        mid_iqr,
        spread_0p001_0p0025_fraction,
        median_spread,
        total_liquidity_usd,
        median_clob_depth_2c_usd,
        median_clob_total_book_notional_usd,
        median_clob_abs_imbalance,
        median_clob_spread
    """

    for event_id, markets in events.items():
        market_count = len(markets)

        event_title = next(
            (
                x["event_title"]
                for x in markets
                if x["event_title"]
            ),
            None,
        )

        mids = [
            x["mid_price"]
            for x in markets
            if x["mid_price"] is not None
        ]

        spreads = [
            x["spread"]
            for x in markets
            if x["spread"] is not None
        ]

        liquidities = [
            x["liquidity_usd"]
            for x in markets
            if x["liquidity_usd"] is not None
        ]

        volumes = [
            x["volume_total_usd"]
            for x in markets
            if x["volume_total_usd"] is not None
        ]

        two_sided_count = sum(
            1
            for x in markets
            if int(x["two_sided"] or 0) == 1
        )

        mid_40_60_count = sum(
            1
            for x in mids
            if 0.40 <= float(x) < 0.60
        )

        spread_target_count = sum(
            1
            for x in spreads
            if 0.001 <= float(x) <= 0.0025
        )

        q25 = _event_quantile(mids, 0.25)
        q50 = _event_quantile(mids, 0.50)
        q75 = _event_quantile(mids, 0.75)

        mid_iqr = (
            q75 - q25
            if q25 is not None and q75 is not None
            else None
        )

        depth2_values = []
        total_book_values = []
        imbalance_values = []
        clob_spread_values = []

        clob_market_count = 0

        for market in markets:
            sides = books.get(
                market["market_id"],
                {},
            )

            yes = sides.get("YES")
            no = sides.get("NO")

            if yes is None or no is None:
                yes = sides.get("OUTCOME_0")
                no = sides.get("OUTCOME_1")

            if yes is None or no is None:
                continue

            clob_market_count += 1

            if (
                yes["quote_state"] == "TWO_SIDED"
                and no["quote_state"] == "TWO_SIDED"
                and yes["spread"] is not None
                and no["spread"] is not None
            ):
                clob_spread_values.append(
                    _event_median([
                        yes["spread"],
                        no["spread"],
                    ])
                )

            depth_parts = [
                yes["bid_depth_2c_usd"],
                yes["ask_depth_2c_usd"],
                no["bid_depth_2c_usd"],
                no["ask_depth_2c_usd"],
            ]

            if all(x is not None for x in depth_parts):
                depth2_values.append(
                    sum(float(x) for x in depth_parts)
                )

            book_parts = [
                yes["total_bid_notional_usd"],
                yes["total_ask_notional_usd"],
                no["total_bid_notional_usd"],
                no["total_ask_notional_usd"],
            ]

            if all(x is not None for x in book_parts):
                total_book_values.append(
                    sum(float(x) for x in book_parts)
                )

            for side in (yes, no):
                bid = side["bid_depth_2c_usd"]
                ask = side["ask_depth_2c_usd"]

                if bid is None or ask is None:
                    continue

                bid = float(bid)
                ask = float(ask)

                if bid + ask > 0:
                    imbalance_values.append(
                        abs(bid - ask) / (bid + ask)
                    )

        metrics = {
            "two_sided_fraction":
                two_sided_count / market_count
                if market_count else 0.0,

            "mid_iqr":
                mid_iqr,

            "spread_0p001_0p0025_fraction":
                spread_target_count / market_count
                if market_count else 0.0,

            "median_spread":
                _event_median(spreads),

            "total_liquidity_usd":
                sum(float(x) for x in liquidities)
                if liquidities else None,

            "median_clob_depth_2c_usd":
                _event_median(depth2_values),

            "median_clob_total_book_notional_usd":
                _event_median(total_book_values),

            "median_clob_abs_imbalance":
                _event_median(imbalance_values),

            "median_clob_spread":
                _event_median(clob_spread_values),
        }

        prior = {}

        for minutes in (15, 30):
            prior_bucket = (
                bucket_dt
                - timedelta(minutes=minutes)
            ).isoformat()

            prior_row = conn.execute(f"""
                SELECT {prior_columns}
                FROM event_measurements
                WHERE event_id = ?
                  AND observation_bucket = ?
            """, (
                event_id,
                prior_bucket,
            )).fetchone()

            if prior_row is None:
                prior[minutes] = None
            else:
                prior[minutes] = {
                    "two_sided_fraction":
                        prior_row[0],
                    "mid_iqr":
                        prior_row[1],
                    "spread_0p001_0p0025_fraction":
                        prior_row[2],
                    "median_spread":
                        prior_row[3],
                    "total_liquidity_usd":
                        prior_row[4],
                    "median_clob_depth_2c_usd":
                        prior_row[5],
                    "median_clob_total_book_notional_usd":
                        prior_row[6],
                    "median_clob_abs_imbalance":
                        prior_row[7],
                    "median_clob_spread":
                        prior_row[8],
                }

        def d(minutes, key):
            prev = prior.get(minutes)

            return _event_delta(
                metrics.get(key),
                prev.get(key) if prev else None,
            )

        rows.append({
            "event_id":
                event_id,
            "event_title":
                event_title,

            "observation_bucket":
                observation_bucket,
            "observed_at":
                observed_at,

            "schema_version":
                "canonical_event_measurement_v2",
            "source_scope_complete_universe":
                0,
            "clob_run_status":
                clob_run_status,

            "market_count":
                market_count,
            "two_sided_count":
                two_sided_count,
            "two_sided_fraction":
                metrics["two_sided_fraction"],

            "priced_market_count":
                len(mids),
            "mid_q25":
                q25,
            "mid_median":
                q50,
            "mid_q75":
                q75,
            "mid_iqr":
                mid_iqr,

            "mid_40_60_count":
                mid_40_60_count,
            "mid_40_60_fraction":
                mid_40_60_count / market_count
                if market_count else 0.0,

            "spread_count":
                len(spreads),
            "median_spread":
                metrics["median_spread"],

            "spread_0p001_0p0025_count":
                spread_target_count,
            "spread_0p001_0p0025_fraction":
                metrics[
                    "spread_0p001_0p0025_fraction"
                ],

            "liquidity_count":
                len(liquidities),
            "total_liquidity_usd":
                metrics["total_liquidity_usd"],
            "median_liquidity_usd":
                _event_median(liquidities),

            "volume_count":
                len(volumes),
            "total_volume_usd":
                sum(float(x) for x in volumes)
                if volumes else None,
            "median_volume_usd":
                _event_median(volumes),

            "clob_market_count":
                clob_market_count,
            "clob_coverage_fraction":
                clob_market_count / market_count
                if market_count else 0.0,

            "clob_depth_2c_market_count":
                len(depth2_values),
            "median_clob_depth_2c_usd":
                metrics[
                    "median_clob_depth_2c_usd"
                ],

            "clob_total_book_market_count":
                len(total_book_values),
            "median_clob_total_book_notional_usd":
                metrics[
                    "median_clob_total_book_notional_usd"
                ],

            "clob_imbalance_side_count":
                len(imbalance_values),
            "median_clob_abs_imbalance":
                metrics[
                    "median_clob_abs_imbalance"
                ],

            "median_clob_spread":
                metrics["median_clob_spread"],

            "delta_15m_two_sided_fraction":
                d(15, "two_sided_fraction"),
            "delta_30m_two_sided_fraction":
                d(30, "two_sided_fraction"),

            "delta_15m_mid_iqr":
                d(15, "mid_iqr"),
            "delta_30m_mid_iqr":
                d(30, "mid_iqr"),

            "delta_15m_spread_0p001_0p0025_fraction":
                d(
                    15,
                    "spread_0p001_0p0025_fraction",
                ),
            "delta_30m_spread_0p001_0p0025_fraction":
                d(
                    30,
                    "spread_0p001_0p0025_fraction",
                ),

            "delta_15m_median_spread":
                d(15, "median_spread"),
            "delta_30m_median_spread":
                d(30, "median_spread"),

            "delta_15m_total_liquidity_usd":
                d(15, "total_liquidity_usd"),
            "delta_30m_total_liquidity_usd":
                d(30, "total_liquidity_usd"),

            "delta_15m_median_clob_depth_2c_usd":
                d(
                    15,
                    "median_clob_depth_2c_usd",
                ),
            "delta_30m_median_clob_depth_2c_usd":
                d(
                    30,
                    "median_clob_depth_2c_usd",
                ),

            "delta_15m_median_clob_total_book_notional_usd":
                d(
                    15,
                    "median_clob_total_book_notional_usd",
                ),
            "delta_30m_median_clob_total_book_notional_usd":
                d(
                    30,
                    "median_clob_total_book_notional_usd",
                ),

            "delta_15m_median_clob_abs_imbalance":
                d(
                    15,
                    "median_clob_abs_imbalance",
                ),
            "delta_30m_median_clob_abs_imbalance":
                d(
                    30,
                    "median_clob_abs_imbalance",
                ),

            "delta_15m_median_clob_spread":
                d(15, "median_clob_spread"),
            "delta_30m_median_clob_spread":
                d(30, "median_clob_spread"),
        })

    if not rows:
        return 0

    columns = list(rows[0].keys())

    sql = f"""
        INSERT OR IGNORE INTO event_measurements (
            {",".join(columns)}
        )
        VALUES (
            {",".join(":" + c for c in columns)}
        )
    """

    before = conn.total_changes
    conn.executemany(sql, rows)

    return conn.total_changes - before


def wait_for_current_raw_bucket(expected, timeout_s=90, poll_s=2):
    """Wait for Gamma's atomic publication of the expected bucket."""
    deadline = time.monotonic() + timeout_s
    last_seen = "MISSING"

    while True:
        if RAW.exists():
            try:
                raw = json.loads(RAW.read_text(encoding="utf-8"))
                bucket = raw.get("observation_bucket")
                last_seen = str(bucket)

                if bucket == expected:
                    return raw

                if bucket:
                    source_dt = datetime.fromisoformat(bucket)
                    expected_dt = datetime.fromisoformat(expected)

                    if source_dt > expected_dt:
                        raise SystemExit(
                            f"FUTURE_RAW_BUCKET expected={expected} "
                            f"actual={bucket}"
                        )
            except (OSError, ValueError) as exc:
                last_seen = f"READ_ERROR:{type(exc).__name__}"

        remaining = deadline - time.monotonic()

        if remaining <= 0:
            raise SystemExit(
                f"STALE_RAW_BUCKET expected={expected} "
                f"actual={last_seen}"
            )

        time.sleep(min(poll_s, remaining))


def main():
    # Source freshness is checked under the collector lock.
    LOCK.parent.mkdir(parents=True, exist_ok=True)

    with LOCK.open("w") as lock_fp:
        try:
            fcntl.flock(
                lock_fp,
                fcntl.LOCK_EX | fcntl.LOCK_NB,
            )
        except BlockingIOError:
            raise SystemExit(
                "ORDERBOOK_COLLECTOR_ALREADY_RUNNING"
            )

        started = datetime.now(timezone.utc)

        expected_dt = started.replace(
            minute=(started.minute // 15) * 15,
            second=0,
            microsecond=0,
        )
        expected_bucket = expected_dt.isoformat()

        raw = wait_for_current_raw_bucket(expected_bucket)
        bucket = raw["observation_bucket"]

        markets = [
            r for r in raw.get("rows", [])
            if r.get("tradable_top_of_book")
        ]

        if not markets:
            raise SystemExit("NO_TRADABLE_MARKETS")

        run_id = uuid.uuid4().hex

        meta = {}
        token_ids = []
        seen_tokens = set()

        for market in markets:
            outcomes = market.get("outcomes")
            tokens = market.get("clob_token_ids")

            if (
                not isinstance(outcomes, list)
                or not isinstance(tokens, list)
                or len(outcomes) != 2
                or len(tokens) != 2
                or not all(str(t).strip() for t in tokens)
                or str(tokens[0]) == str(tokens[1])
            ):
                raise RuntimeError(
                    "INVALID_BINARY_TOKEN_MAPPING "
                    f"market={market.get('market_id')}"
                )

            labels = [
                str(x).strip().lower()
                for x in outcomes
            ]

            sides = (
                ("YES", "NO")
                if labels == ["yes", "no"]
                else ("OUTCOME_0", "OUTCOME_1")
            )

            for i, (side, token) in enumerate(
                zip(sides, tokens)
            ):
                token = str(token)

                if token in seen_tokens:
                    raise RuntimeError(
                        "DUPLICATE_CLOB_TOKEN "
                        f"token={token}"
                    )

                seen_tokens.add(token)
                token_ids.append(token)

                meta[token] = {
                    "market_id": str(market["market_id"]),
                    "market_name": market["market_name"],
                    "outcome_side": side,
                    "outcome_label": str(outcomes[i]),
                }

        client = ClobClient(HOST)

        returned = {}
        failed_tokens = set()
        batch_failures = 0

        t0 = time.time()

        for i in range(0, len(token_ids), BATCH_SIZE):
            chunk = token_ids[i:i + BATCH_SIZE]

            try:
                books = client.get_order_books(
                    [
                        BookParams(token_id=t)
                        for t in chunk
                    ]
                )

                for book in books:
                    token = book_token(book)

                    if token:
                        returned[token] = book

            except Exception:
                batch_failures += 1
                failed_tokens.update(chunk)

        latency_ms = round(
            (time.time() - t0) * 1000,
            1,
        )

        observed_at = datetime.now(
            timezone.utc
        ).isoformat()

        rows = []

        for token in token_ids:
            m = meta[token]

            if token in failed_tokens:
                row = {
                    **m,
                    "token_id": token,
                    "observation_bucket": bucket,
                    "observed_at": observed_at,
                    "collection_status": "BATCH_ERROR",
                    "quote_state": None,
                }

            elif token not in returned:
                row = {
                    **m,
                    "token_id": token,
                    "observation_bucket": bucket,
                    "observed_at": observed_at,
                    "collection_status":
                        "MISSING_RESPONSE",
                    "quote_state": None,
                }

            else:
                metrics = summarize_book(
                    returned[token]
                )

                row = {
                    **m,
                    "token_id": token,
                    "observation_bucket": bucket,
                    "observed_at": observed_at,
                    "collection_status": "OK",
                    **metrics,
                }

            rows.append(row)

        columns = [
            "market_id", "market_name",
            "token_id", "outcome_side",
            "observation_bucket", "observed_at",
            "collection_status", "quote_state",
            "best_bid", "best_ask", "spread",
            "bid_levels", "ask_levels",
            "top_bid_size", "top_ask_size",
            "total_bid_shares", "total_ask_shares",
            "total_bid_notional_usd",
            "total_ask_notional_usd",
            "bid_depth_1c_usd", "ask_depth_1c_usd",
            "bid_depth_2c_usd", "ask_depth_2c_usd",
            "bid_depth_5c_usd", "ask_depth_5c_usd",
            "buy_vwap_10", "buy_fill_10",
            "buy_vwap_50", "buy_fill_50",
            "buy_vwap_100", "buy_fill_100",
            "sell_vwap_10", "sell_fill_10",
            "sell_vwap_50", "sell_fill_50",
            "sell_vwap_100", "sell_fill_100",
        ]

        placeholders = ",".join(
            f":{c}" for c in columns
        )

        sql = f"""
            INSERT OR IGNORE INTO clob_books (
                {",".join(columns)}
            )
            VALUES ({placeholders})
        """

        with sqlite3.connect(DB) as conn:
            init_db(conn)
            init_event_measurements_db(conn)

            before = conn.total_changes

            normalized = [
                {c: row.get(c) for c in columns}
                for row in rows
            ]

            conn.executemany(sql, normalized)

            inserted = (
                conn.total_changes - before
            )

            missing = sum(
                1 for r in rows
                if r["collection_status"]
                == "MISSING_RESPONSE"
            )

            status = (
                "OK"
                if batch_failures == 0
                and missing == 0
                else "PARTIAL"
            )

            event_measurements_inserted = 0

            if status == "OK":
                event_measurements_inserted = (
                    write_event_measurements(
                        conn,
                        bucket,
                        observed_at,
                        status,
                    )
                )

            conn.execute("""
                INSERT INTO clob_collection_runs (
                    run_id,
                    observation_bucket,
                    started_at,
                    completed_at,
                    markets_requested,
                    tokens_requested,
                    books_returned,
                    batch_failures,
                    missing_tokens,
                    status,
                    latency_ms
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                run_id,
                bucket,
                started.isoformat(),
                datetime.now(timezone.utc).isoformat(),
                len(markets),
                len(token_ids),
                len(returned),
                batch_failures,
                missing,
                status,
                latency_ms,
            ))

            conn.commit()

        market_rows = []

        by_market = {}

        for row in rows:
            by_market.setdefault(
                row["market_id"],
                {
                    "market_id": row["market_id"],
                    "market_name": row["market_name"],
                    "observation_bucket": bucket,
                },
            )

            output_row = dict(row)
            output_row["outcome_label"] = meta[
                row["token_id"]
            ]["outcome_label"]

            by_market[row["market_id"]][
                row["outcome_side"].lower()
            ] = output_row

        market_rows = list(by_market.values())

        OUT.write_text(
            json.dumps(
                {
                    "schema_version":
                        "clob_execution_measurement_v1",
                    "timestamp": observed_at,
                    "observation_bucket": bucket,
                    "count": len(market_rows),
                    "tokens": len(rows),
                    "rows": market_rows,
                },
                indent=2,
            )
        )

        print("REAL_CLOB_ORDERBOOK_COLLECTOR")
        print("markets =", len(markets))
        print("tokens_requested =", len(token_ids))
        print("books_returned =", len(returned))
        print("batch_failures =", batch_failures)
        print("missing_tokens =", missing)
        print("latency_ms =", latency_ms)
        print("db_rows_inserted =", inserted)
        print(
            "event_measurements_inserted =",
            event_measurements_inserted,
        )
        print("bucket =", bucket)


if __name__ == "__main__":
    main()
