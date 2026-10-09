import json
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))

import api_server
import system_monitor
from fastapi import HTTPException


class ReliabilityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.health_file = Path(self.tmp.name) / "health.json"
        self.patch_health = patch.object(api_server, "HEALTH", self.health_file)
        self.patch_health.start()
        self.addCleanup(self.patch_health.stop)

    def write_health(self, state, generated_at=None):
        self.health_file.write_text(json.dumps({
            "generated_at": generated_at or datetime.now(timezone.utc).isoformat(),
            "reliability": {"state": state},
        }))

    def test_healthy_and_pending(self):
        for state in ("HEALTHY", "PENDING"):
            with self.subTest(state=state):
                self.write_health(state)
                result = api_server.health()
                self.assertEqual(result["measurement"]["reliability"]["state"], state)

    def test_degraded(self):
        self.write_health("DEGRADED")
        with self.assertRaises(HTTPException) as caught:
            api_server.health()
        self.assertEqual(caught.exception.status_code, 503)
        self.assertEqual(
            caught.exception.detail["reason"],
            "measurement_reliability_degraded",
        )

    def test_invalid_and_missing(self):
        self.write_health("UNKNOWN")
        with self.assertRaises(HTTPException) as caught:
            api_server.health()
        self.assertEqual(caught.exception.status_code, 503)

        self.health_file.unlink()
        with self.assertRaises(HTTPException) as caught:
            api_server.health()
        self.assertEqual(caught.exception.status_code, 503)

    def test_stale_and_future(self):
        now = datetime.now(timezone.utc)
        for timestamp in (
            now - timedelta(seconds=1900),
            now + timedelta(seconds=120),
        ):
            with self.subTest(timestamp=timestamp):
                self.write_health("HEALTHY", timestamp.isoformat())
                with self.assertRaises(HTTPException) as caught:
                    api_server.health()
                self.assertEqual(caught.exception.status_code, 503)

    def test_monitor_states(self):
        now = datetime(2026, 10, 9, 12, 2, tzinfo=timezone.utc)
        bucket = now.replace(minute=0, second=0)
        expected = bucket.isoformat()
        observed = now.isoformat()
        run = {
            "observation_bucket": expected,
            "status": "OK",
            "tokens_requested": 4,
            "books_returned": 4,
            "batch_failures": 0,
            "missing_tokens": 0,
        }

        def evaluate(moment, gamma, clob, current_run=run):
            return system_monitor.evaluate_reliability(
                moment, gamma, clob, 2, 2, 4,
                current_run, observed, observed,
            )["state"]

        self.assertEqual(evaluate(now, expected, expected), "HEALTHY")
        self.assertEqual(evaluate(now, None, None, None), "PENDING")
        self.assertEqual(
            evaluate(now + timedelta(minutes=7), None, None, None),
            "DEGRADED",
        )
        self.assertEqual(
            evaluate(now, expected, expected, {**run, "books_returned": 3}),
            "DEGRADED",
        )


if __name__ == "__main__":
    unittest.main()
