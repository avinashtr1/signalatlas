"""Regression tests for event research eligibility."""

import sqlite3
import unittest

from polymarket_engine.event_research_eligibility import eligible_events

V1 = "canonical_event_measurement_v1"
V2 = "canonical_event_measurement_v2"


class EligibilityTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        self.db.execute("""
            CREATE TABLE event_measurements (
                event_id TEXT,
                observation_bucket TEXT,
                schema_version TEXT,
                market_count INTEGER,
                clob_coverage_fraction REAL,
                delta_15m_mid_iqr REAL,
                delta_30m_mid_iqr REAL,
                PRIMARY KEY(event_id, observation_bucket)
            )
        """)

    def tearDown(self):
        self.db.close()

    def add(self, minute, version, d15=None, d30=None):
        self.db.execute("""
            INSERT INTO event_measurements (
                event_id, observation_bucket, schema_version,
                market_count, clob_coverage_fraction,
                delta_15m_mid_iqr, delta_30m_mid_iqr
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            "event-A",
            f"2026-09-29T17:{minute:02d}:00+00:00",
            version, 10, 0.6, d15, d30,
        ))

    def test_cross_schema_both_horizons(self):
        self.add(0, V1)
        self.add(15, V1)
        self.add(30, V2, 0.2, 0.3)
        row = list(eligible_events(self.db))[-1]
        self.assertIsNone(row["delta_15m_mid_iqr"])
        self.assertIsNone(row["delta_30m_mid_iqr"])

    def test_valid_15m_and_invalid_30m(self):
        self.add(0, V1)
        self.add(15, V2)
        self.add(30, V2, 0.2, 0.3)
        row = list(eligible_events(self.db))[-1]
        self.assertEqual(row["delta_15m_mid_iqr"], 0.2)
        self.assertIsNone(row["delta_30m_mid_iqr"])

    def test_missing_prior_and_coverage_preserved(self):
        self.add(30, V2, 0.2, 0.3)
        row = list(eligible_events(self.db))[0]
        self.assertIsNone(row["delta_15m_mid_iqr"])
        self.assertIsNone(row["delta_30m_mid_iqr"])
        self.assertEqual(row["market_count"], 10)
        self.assertEqual(row["clob_coverage_fraction"], 0.6)




    def test_all_delta_metrics(self):
        metrics = (
            "two_sided_fraction",
            "mid_iqr",
            "spread_0p001_0p0025_fraction",
            "median_spread",
            "total_liquidity_usd",
            "median_clob_depth_2c_usd",
            "median_clob_total_book_notional_usd",
            "median_clob_abs_imbalance",
            "median_clob_spread",
        )

        for h in (15, 30):
            for metric in metrics:
                col = f"delta_{h}m_{metric}"
                if metric != "mid_iqr":
                    self.db.execute(
                        f"ALTER TABLE event_measurements ADD COLUMN {col} REAL"
                    )

        self.add(0, V1)
        self.add(15, V1)
        self.add(30, V2, 0.2, 0.3)

        for h in (15, 30):
            for metric in metrics:
                col = f"delta_{h}m_{metric}"
                self.db.execute(
                    f"UPDATE event_measurements SET {col}=0.25 "
                    "WHERE schema_version=?", (V2,)
                )

        row = list(eligible_events(self.db))[0]

        for h in (15, 30):
            for metric in metrics:
                self.assertIsNone(row[f"delta_{h}m_{metric}"])

        self.assertEqual(row["market_count"], 10)
        self.assertEqual(row["clob_coverage_fraction"], 0.6)

if __name__ == "__main__":
    unittest.main()
