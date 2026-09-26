class MarketFilterConfig:
    def __init__(self):
        self.max_duration_hours = 168
        self.min_annualized_edge_percent = 20
        self.min_raw_edge_percent = 0.01

        self.trigger_market_mappings = {
            "price_momentum_burst": {
                "priority": "high",
                "market_types": ["crypto", "event"],
                "duration_filter_hours": 72,
            },
            "volatility_spike": {
                "priority": "high",
                "market_types": ["crypto", "event"],
                "duration_filter_hours": 72,
            },
            "time_to_resolution_critical": {
                "priority": "critical",
                "market_types": ["crypto", "event"],
                "duration_filter_hours": 12,
            },
        }
