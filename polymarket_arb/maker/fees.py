"""
Fee Management Module

Responsibility:
- Fetch and store current maker/taker fee rates.
- Provide fee data to the quoter and evaluator.
- Fallback to safe defaults if API is unreachable.
"""

import os
import json
import time

# Default safe fallback (e.g. 20bps taker if unknown, though PM is usually 0 maker / 2% taker on some matchings)
# Polymarket CTF/neg risk fees vary.
DEFAULT_TAKER_FEE_BPS = 20
DEFAULT_MAKER_FEE_BPS = 0 

class FeeManager:
    def __init__(self):
        self.fees = {
            "maker_bps": DEFAULT_MAKER_FEE_BPS,
            "taker_bps": DEFAULT_TAKER_FEE_BPS,
            "last_updated": 0
        }
    
    def update_fees(self):
        """
        Fetch current fees from API (Mocked for now).
        TODO: Implement real API call to Polymarket/Exchange.
        """
        # Mock update
        self.fees["maker_bps"] = 0
        self.fees["taker_bps"] = 10 # Example: 0.1% taker
        self.fees["last_updated"] = time.time()
        
    def get_maker_bps(self):
        if time.time() - self.fees["last_updated"] > 3600:
            self.update_fees()
        return self.fees["maker_bps"]

    def get_taker_bps(self):
        if time.time() - self.fees["last_updated"] > 3600:
            self.update_fees()
        return self.fees["taker_bps"]

# Global singleton
fee_manager = FeeManager()
