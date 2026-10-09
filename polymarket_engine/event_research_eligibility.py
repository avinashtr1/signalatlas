"""Read-only eligibility for prospective V2 event measurement research."""

import sqlite3

SCHEMA = "canonical_event_measurement_v2"
HORIZONS = (15, 30)


def eligible_events(conn):
    """Return V2 measurements with schema-safe horizon deltas.

    Historical deltas are NULL when the exact prior V2 observation
    is absent. Raw measurements and coverage counts remain unchanged.

    Research eligibility limitations:
    - V2 observations represent the measured event population, not
      necessarily the complete market universe.
    - source_scope_complete_universe=0 prohibits complete-universe claims.
    - market_count is the observed event denominator.
    - priced_market_count, spread_count, liquidity_count, and CLOB
      metric-specific counts describe measurement completeness.
    - clob_imbalance_side_count counts outcome sides, not markets.
    - Partial CLOB coverage must not be interpreted as complete-event
      microstructure.
    - Coverage strata are descriptive, not optimized alpha thresholds.
    - NULL measurements remain missing; no imputation is performed.
    - This function does not certify statistical significance,
      causal effects, executable profitability, or Brain permission.
    """
    columns = [
        row[1]
        for row in conn.execute("PRAGMA table_info(event_measurements)")
    ]

    selected = [
        f"e.{column}"
        for column in columns
        if not column.startswith(("delta_15m_", "delta_30m_"))
    ]

    for minutes in HORIZONS:
        alias = f"p{minutes}"
        selected.extend(
            f"CASE WHEN {alias}.event_id IS NOT NULL "
            f"THEN e.{column} ELSE NULL END AS {column}"
            for column in columns
            if column.startswith(f"delta_{minutes}m_")
        )

    joins = []
    for minutes in HORIZONS:
        alias = f"p{minutes}"
        joins.append(f"""
            LEFT JOIN event_measurements {alias}
              ON {alias}.event_id = e.event_id
             AND {alias}.observation_bucket =
                 strftime('%Y-%m-%dT%H:%M:%S+00:00',
                          datetime(e.observation_bucket, '-{minutes} minutes'))
             AND {alias}.schema_version = ?
        """)

    query = f"""
        SELECT {', '.join(selected)}
        FROM event_measurements e
        {' '.join(joins)}
        WHERE e.schema_version = ?
        ORDER BY e.observation_bucket, e.event_id
    """

    cursor = conn.execute(query, (SCHEMA, SCHEMA, SCHEMA))
    names = [item[0] for item in cursor.description]

    for row in cursor:
        yield dict(zip(names, row))


def open_readonly(path):
    """Open the canonical SQLite database without write permission."""
    return sqlite3.connect(
        f"file:{path}?mode=ro",
        uri=True,
    )
