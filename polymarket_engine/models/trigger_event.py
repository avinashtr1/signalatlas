from datetime import datetime

class TriggerEvent:
    def __init__(self,
                 trigger_type: str, source_venue: str, source_symbol: str,
                 trigger_timestamp: datetime, details: dict | None = None):
        self.trigger_type, self.source_venue, self.source_symbol = trigger_type, source_venue, source_symbol
        self.trigger_timestamp = trigger_timestamp
        self.details: dict = details if details else {}
