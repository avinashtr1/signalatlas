import json
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta

from ..models.trigger_event import TriggerEvent


class PolymarketAdapter:
    BASE_EVENTS_URL = "https://gamma-api.polymarket.com/events"
    BASE_MARKETS_URL = "https://gamma-api.polymarket.com/markets"

    def __init__(self, timeout=10):
        self.timeout = timeout

    def _http_get_json(self, url: str):
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "OpenClaw-PolymarketEngine/1.0",
                "Accept": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def _safe_float(self, value, default=0.0):
        try:
            if value is None or value == "":
                return default
            return float(value)
        except Exception:
            return default

    def _parse_json_list(self, raw):
        if raw is None:
            return []
        if isinstance(raw, list):
            return raw
        if isinstance(raw, str):
            try:
                return json.loads(raw)
            except Exception:
                return []
        return []

    def _pick_end_time(self, obj: dict):
        for key in ["endDate", "end_date", "endTime", "end_time"]:
            if obj.get(key):
                return obj.get(key)
        return (datetime.now(timezone.utc) + timedelta(days=7)).isoformat().replace("+00:00", "Z")

    def _extract_yes_price(self, market: dict):
        outcome_prices = self._parse_json_list(market.get("outcomePrices"))
        if outcome_prices:
            v = self._safe_float(outcome_prices[0], 0.5)
            if v > 1.0:
                v = v / 100.0
            return max(0.01, min(0.99, v))

        for key in ["lastTradePrice", "price", "probability"]:
            if market.get(key) is not None:
                v = self._safe_float(market.get(key), 0.5)
                if v > 1.0:
                    v = v / 100.0
                return max(0.01, min(0.99, v))

        return 0.5

    def _extract_volume(self, market: dict):
        for key in ["volumeNum", "volume", "liquidityNum", "liquidity", "volume24hr", "volume1wk", "volume1mo"]:
            if market.get(key) is not None:
                v = self._safe_float(market.get(key), 0.0)
                if v > 0:
                    return v
        return 50000.0

    def _extract_market_id(self, market: dict):
        for key in ["id", "market_id", "conditionId", "condition_id", "slug"]:
            if market.get(key):
                return str(market.get(key))
        return str(hash(json.dumps(market, sort_keys=True)))


    def _is_likely_exclusive_bucket(self, title: str, count: int) -> bool:
        t = (title or "").lower().strip()

        positive_patterns = [
            "winner",
            "nominee",
            "which party will win",
            "balance of power",
            "prison time",
            "champion",
            "mvp",
            "rookie of the year",
            "conference champion",
        ]

        negative_patterns = [
            "qualify",
            "before",
            " by ",
            "reach",
            "make",
            "appear",

            "qualify",
            "before gta vi",
            "before june",
            "before july",
            "before august",
            "before september",
            "before october",
            "before november",
            "before december",
            "by march",
            "by april",
            "by may",
            "by june",
            "by july",
            "by august",
            "by september",
            "by october",
            "by november",
            "by december",
            "capture",
            "out by",
            "sells any",
        ]

        if count < 2:
            return False

        for bad in negative_patterns:
            if bad in t:
                return False

        for good in positive_patterns:
            if good in t:
                return True

        return False

    def _normalize_bucket_event_markets(self, event: dict):
        event_id = str(event.get("id"))
        event_title = event.get("title") or event.get("slug") or f"event_{event_id}"
        event_category = (event.get("category") or "event").lower()
        markets = event.get("markets") or []

        live_markets = []
        for m in markets:
            if bool(m.get("closed")):
                continue
            if bool(m.get("archived")):
                continue
            if m.get("acceptingOrders") is False:
                continue
            live_markets.append(m)

        yes_prices = []
        normalized = []
        is_exclusive_bucket = self._is_likely_exclusive_bucket(event_title, len(live_markets))

        # first pass: collect yes prices
        for m in live_markets:
            yes_prices.append(self._extract_yes_price(m))

        # second pass: normalize each market with bucket group metadata
        for idx, m in enumerate(live_markets):
            # only keep genuinely tradable live child markets
            if bool(m.get("closed")):
                continue
            if bool(m.get("archived")):
                continue
            if m.get("acceptingOrders") is False:
                continue

            market_id = self._extract_market_id(m)
            name = m.get("question") or m.get("title") or m.get("slug") or f"Market {market_id}"
            current_price = self._extract_yes_price(m)
            volume = self._extract_volume(m)
            group_item_title = (m.get("groupItemTitle") or "").strip()

            normalized.append({
                "market_id": market_id,
                "name": name,
                "end_time": self._pick_end_time(m),
                "current_price": current_price,
                "liquidity_snapshot": {
                    "volume_usd": volume,
                    "depth_bps": 75,
                },
                "truth_source": "Polymarket Gamma API",
                "truth_source_confidence": 0.95,
                "objective_support": True,
                "market_type": "crypto" if any(x in (name + " " + event_title).lower() for x in ["btc", "bitcoin", "eth", "ethereum", "sol", "crypto"]) else "event",
                "event_group": event_title,
                "relation_type": "bucket_member" if is_exclusive_bucket else "standalone",
                "bucket_group_id": event_id if is_exclusive_bucket else None,
                "bucket_group_title": event_title if is_exclusive_bucket else None,
                "bucket_group_prices": yes_prices if is_exclusive_bucket else [],
                "group_item_title": group_item_title,
                "conditionId": m.get("conditionId"),
                "slug": m.get("slug"),
            })

        return normalized

    def _fetch_active_events(self, limit=250):
        params = {
            "active": "true",
            "closed": "false",
            "archived": "false",
            "limit": str(limit),
        }
        url = self.BASE_EVENTS_URL + "?" + urllib.parse.urlencode(params)
        data = self._http_get_json(url)
        return data if isinstance(data, list) else []

    def _fetch_active_markets(self, limit=500):
        params = {
            "active": "true",
            "closed": "false",
            "limit": str(limit),
        }
        url = self.BASE_MARKETS_URL + "?" + urllib.parse.urlencode(params)
        data = self._http_get_json(url)
        return data if isinstance(data, list) else []


    def get_market_by_id(self, market_id: str) -> dict:
        url = f"{self.BASE_MARKETS_URL}/{market_id}"
        raw = self._http_get_json(url)

        return {
            "market_id": self._extract_market_id(raw),
            "name": raw.get("question") or raw.get("title") or raw.get("slug") or f"Market {market_id}",
            "end_time": self._pick_end_time(raw),
            "current_price": self._extract_yes_price(raw),
            "liquidity_snapshot": {
                "volume_usd": self._extract_volume(raw),
                "depth_bps": 75,
            },
            "truth_source": "Polymarket Gamma API",
            "truth_source_confidence": 0.95,
            "objective_support": True,
            "market_type": "event",
            "event_group": raw.get("groupItemTitle") or "POLYMARKET",
            "relation_type": raw.get("relation_type", "standalone"),
            "bucket_group_id": None,
            "bucket_group_title": None,
            "bucket_group_prices": [],
            "group_item_title": raw.get("groupItemTitle", ""),
            "conditionId": raw.get("conditionId"),
            "slug": raw.get("slug"),
            "active": raw.get("active"),
            "closed": raw.get("closed"),
            "archived": raw.get("archived"),
            "outcomes": self._parse_json_list(raw.get("outcomes")),
            "outcomePrices": self._parse_json_list(raw.get("outcomePrices")),
            "updatedAt": raw.get("updatedAt"),
        }


    def _is_repetitive_live_family(self, title: str) -> bool:
        t = (title or "").lower()
        bad_patterns = [
            " by march",
            " by april",
            " by may",
            " by june",
            " by july",
            " by august",
            " by september",
            " by october",
            " by november",
            " by december",
            " before gta vi",
            "out by...?",
            " called by...?",
            " held by...?",
        ]
        return any(x in t for x in bad_patterns)

    def _diversify_live_markets(self, markets: list[dict], max_per_group=6):
        grouped = {}
        for m in markets:
            group = m.get("bucket_group_title") or m.get("event_group") or "UNGROUPED"
            title = str(group)

            if self._is_repetitive_live_family(title):
                continue

            grouped.setdefault(group, []).append(m)

        out = []
        for group, items in grouped.items():
            items = sorted(
                items,
                key=lambda x: float((x.get("liquidity_snapshot") or {}).get("volume_usd", 0.0) or 0.0),
                reverse=True,
            )
            out.extend(items[:max_per_group])

        return out


    def get_markets_for_trigger(self, trigger_event: TriggerEvent) -> list[dict]:
        events = self._fetch_active_events(limit=250)
        normalized = []

        for e in events:
            normalized.extend(self._normalize_bucket_event_markets(e))

        # fallback if events endpoint returns nothing useful
        if not normalized:
            raw_markets = self._fetch_active_markets(limit=500)
            for m in raw_markets:
                market_id = self._extract_market_id(m)
                name = m.get("question") or m.get("title") or m.get("slug") or f"Market {market_id}"
                normalized.append({
                    "market_id": market_id,
                    "name": name,
                    "end_time": self._pick_end_time(m),
                    "current_price": self._extract_yes_price(m),
                    "liquidity_snapshot": {
                        "volume_usd": self._extract_volume(m),
                        "depth_bps": 75,
                    },
                    "truth_source": "Polymarket Gamma API",
                    "truth_source_confidence": 0.95,
                    "objective_support": True,
                    "market_type": "event",
                    "event_group": "POLYMARKET",
                    "relation_type": "standalone",
                    "bucket_group_id": None,
                    "bucket_group_title": None,
                    "bucket_group_prices": [],
                    "group_item_title": "",
                    "conditionId": m.get("conditionId"),
                    "slug": m.get("slug"),
                })

        symbol = (trigger_event.source_symbol or "").upper()
        if trigger_event.trigger_type == "market_scan" or symbol in ["ALL", ""]:
            return self._diversify_live_markets(normalized)

        filtered = []
        for m in normalized:
            text = (m["name"] + " " + str(m.get("event_group") or "") + " " + str(m.get("bucket_group_title") or "")).upper()
            if symbol in text:
                filtered.append(m)

        return self._diversify_live_markets(filtered if filtered else normalized)
