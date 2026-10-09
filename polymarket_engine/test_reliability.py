import json
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))

import api_server
from polymarket_engine import system_monitor
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


class ReliabilityHistoryTests(unittest.TestCase):
    def test_transitions_and_recovery(self):
        from reliability_history import record_transition

        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "history.jsonl"
            t = "2026-10-09T10:00:00+00:00"

            baseline = record_transition(path, t, "HEALTHY", [])
            self.assertEqual(baseline["event"], "BASELINE")
            self.assertIsNone(baseline["previous_state"])

            self.assertIsNone(
                record_transition(path, t, "HEALTHY", [])
            )

            pending = record_transition(
                path, t, "PENDING", ["CLOB_CURRENT_BUCKET_MISSING"]
            )
            self.assertEqual(pending["event"], "TRANSITION")

            degraded = record_transition(
                path, t, "DEGRADED", ["CLOB_CURRENT_BUCKET_MISSING"]
            )
            self.assertEqual(degraded["previous_state"], "PENDING")

            recovered = record_transition(path, t, "HEALTHY", [])
            self.assertEqual(recovered["event"], "RECOVERED")
            self.assertEqual(recovered["previous_state"], "DEGRADED")

            events = [
                json.loads(line)
                for line in path.read_text().splitlines()
            ]
            self.assertEqual(len(events), 4)

    def test_invalid_state_and_missing_history(self):
        from reliability_history import record_transition

        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "history.jsonl"
            self.assertFalse(path.exists())

            with self.assertRaises(ValueError):
                record_transition(path, "2026-10-09T10:00:00Z", "UNKNOWN", [])

            self.assertFalse(path.exists())


class ReliabilityHistoryApiTests(unittest.TestCase):
    def test_history_endpoint(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            history = root / "analytics" / "reliability_incidents.jsonl"
            history.parent.mkdir()

            with patch.object(api_server, "ROOT", root):
                empty = api_server.reliability_history(limit=50)
                self.assertEqual(empty["events"], [])
                self.assertIsNone(empty["uptime_percent"])
                self.assertEqual(empty["uptime_status"], "INSUFFICIENT_DATA")

                records = [
                    {"observed_at": "2026-10-09T04:00:00Z", "state": "HEALTHY"},
                    {"observed_at": "2026-10-09T04:15:00Z", "state": "DEGRADED"},
                    {"observed_at": "2026-10-09T04:30:00Z", "state": "HEALTHY"},
                ]
                history.write_text(
                    "".join(json.dumps(x) + "\n" for x in records)
                )

                result = api_server.reliability_history(limit=2)
                self.assertEqual(result["count"], 2)
                self.assertEqual(
                    [x["state"] for x in result["events"]],
                    ["HEALTHY", "DEGRADED"],
                )
                self.assertIsNone(result["uptime_percent"])


class ReliabilityHistoryHardeningTests(unittest.TestCase):
    def test_malformed_records_and_state_continuity(self):
        from reliability_history import read_events, record_transition

        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "history.jsonl"
            path.write_text(
                '{"observed_at":"2026-10-09T01:00:00Z","state":"DEGRADED"}\n'
                'not-json\n'
                '{"state":"UNKNOWN","observed_at":"2026-10-09T02:00:00Z"}\n'
                '{"state":"HEALTHY"}\n'
            )

            self.assertEqual(len(read_events(path)), 1)

            event = record_transition(
                path, "2026-10-09T03:00:00Z", "HEALTHY", []
            )
            self.assertEqual(event["event"], "RECOVERED")
            self.assertEqual(event["previous_state"], "DEGRADED")

            self.assertIsNone(
                record_transition(
                    path, "2026-10-09T04:00:00Z", "HEALTHY", []
                )
            )

            self.assertEqual(len(read_events(path)), 2)

    def test_retention_preserves_latest_events(self):
        from unittest.mock import patch as mock_patch
        import reliability_history as rh

        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "history.jsonl"

            with mock_patch.object(rh, "MAX_EVENTS", 3):
                for i, state in enumerate(
                    ["HEALTHY", "PENDING", "DEGRADED", "HEALTHY", "PENDING"]
                ):
                    rh.record_transition(path, str(i), state, [])

            events = rh.read_events(path)
            self.assertEqual(len(events), 3)
            self.assertEqual(
                [e["state"] for e in events],
                ["DEGRADED", "HEALTHY", "PENDING"],
            )
            self.assertEqual(len(path.read_text().splitlines()), 3)

    def test_api_skips_corrupted_history(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            history = root / "analytics" / "reliability_incidents.jsonl"
            history.parent.mkdir()
            history.write_text(
                '{"observed_at":"2026-10-09T01:00:00Z","state":"HEALTHY"}\n'
                'broken-json\n'
                '{"observed_at":"2026-10-09T02:00:00Z","state":"DEGRADED"}\n'
            )

            with patch.object(api_server, "ROOT", root):
                result = api_server.reliability_history(limit=50)

            self.assertEqual(result["count"], 2)
            self.assertEqual(
                [e["state"] for e in result["events"]],
                ["DEGRADED", "HEALTHY"],
            )
            self.assertIsNone(result["uptime_percent"])


class ReliabilityLifecycleTests(unittest.TestCase):
    def test_pending_degraded_recovered_lifecycle(self):
        from reliability_history import record_transition, read_events

        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            health_file = root / "health.json"
            history = root / "incidents.jsonl"

            bucket = datetime(2026, 10, 9, 12, 0, tzinfo=timezone.utc)
            run = {
                "observation_bucket": bucket.isoformat(),
                "status": "OK",
                "tokens_requested": 4,
                "books_returned": 4,
                "batch_failures": 0,
                "missing_tokens": 0,
            }

            def observe(moment, available):
                expected = bucket.isoformat() if available else None
                result = system_monitor.evaluate_reliability(
                    moment,
                    expected,
                    expected,
                    2,
                    2,
                    4,
                    run if available else None,
                    moment.isoformat(),
                    moment.isoformat(),
                )
                record_transition(
                    history,
                    moment.isoformat(),
                    result["state"],
                    result["reasons"],
                )
                health_file.write_text(json.dumps({
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "reliability": result,
                }))
                return result

            with patch.object(api_server, "HEALTH", health_file):
                healthy = observe(bucket + timedelta(minutes=1), True)
                self.assertEqual(healthy["state"], "HEALTHY")
                self.assertEqual(
                    api_server.health()["measurement"]["reliability"]["state"],
                    "HEALTHY",
                )

                pending = observe(bucket + timedelta(minutes=2), False)
                self.assertEqual(pending["state"], "PENDING")
                self.assertEqual(
                    api_server.health()["measurement"]["reliability"]["state"],
                    "PENDING",
                )

                degraded = observe(bucket + timedelta(minutes=7), False)
                self.assertEqual(degraded["state"], "DEGRADED")
                with self.assertRaises(HTTPException) as caught:
                    api_server.health()
                self.assertEqual(caught.exception.status_code, 503)

                recovered = observe(bucket + timedelta(minutes=8), True)
                self.assertEqual(recovered["state"], "HEALTHY")
                self.assertEqual(
                    api_server.health()["measurement"]["reliability"]["state"],
                    "HEALTHY",
                )

            events = read_events(history)
            self.assertEqual(
                [event["state"] for event in events],
                ["HEALTHY", "PENDING", "DEGRADED", "HEALTHY"],
            )
            self.assertEqual(
                [event["event"] for event in events],
                ["BASELINE", "TRANSITION", "TRANSITION", "RECOVERED"],
            )
            self.assertEqual(
                events[-1]["previous_state"],
                "DEGRADED",
            )
