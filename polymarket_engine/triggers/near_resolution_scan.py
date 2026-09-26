from datetime import datetime, timezone, timedelta
from polymarket_engine.models.trigger_event import TriggerEvent


class NearResolutionScanner:

    def __init__(self, hours_window=72):
        self.hours_window = hours_window

    def generate_trigger(self):

        now = datetime.now(timezone.utc)

        return TriggerEvent(
            "near_resolution_scan",
            "system",
            "ALL",
            now,
            {
                "resolution_before": now + timedelta(hours=self.hours_window)
            }
        )
