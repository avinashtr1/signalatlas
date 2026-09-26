from datetime import datetime, timezone


class BasketBuilder:
    """
    Canonical structural-group analysis.

    Current status:
    - STANDARD_NEGRISK groups may be analyzed.
    - AUGMENTED_NEGRISK groups fail closed.
    - This module produces read-only group snapshots.
    - It does NOT allocate capital or execute multi-leg baskets yet.
    """

    def build_baskets(self, acceptable_candidates):
        """
        Legacy API intentionally disabled.

        Structural edge is a group-level property and cannot be safely built
        from already-accepted single-child candidates.
        """
        return []

    def build_group_snapshots(self, adapter, limit=100):
        events = adapter._fetch_active_events(limit=limit)
        observed_at = datetime.now(timezone.utc).isoformat()

        groups = []

        for event in events:
            if event.get("negRisk") is not True:
                continue

            augmented = event.get("negRiskAugmented") is True

            # Augmented NegRisk is intentionally excluded from structural
            # trading analysis until its dynamic outcome semantics are handled.
            if augmented:
                continue

            event_group_id = str(event.get("id"))
            neg_risk_market_id = event.get("negRiskMarketID")
            title = (
                event.get("title")
                or event.get("slug")
                or f"event_{event_group_id}"
            )

            raw_children = [
                m for m in (event.get("markets") or [])
                if m.get("negRisk") is True
            ]

            legs = []
            reference_prices = []
            asks = []
            bids = []

            group_id_consistent = True
            all_orderable = True
            all_asks_present = True
            all_bids_present = True

            for m in raw_children:
                child_group_id = m.get("negRiskMarketID")

                if (
                    neg_risk_market_id
                    and child_group_id
                    and child_group_id != neg_risk_market_id
                ):
                    group_id_consistent = False

                quote = adapter._extract_quote_snapshot(m)
                reference_price = adapter._extract_yes_price(m)

                active = m.get("active") is True
                closed = m.get("closed") is True
                archived = m.get("archived") is True
                accepting_orders = m.get("acceptingOrders") is True

                orderable = (
                    active
                    and not closed
                    and not archived
                    and accepting_orders
                )

                best_bid = quote.get("best_bid")
                best_ask = quote.get("best_ask")

                if not orderable:
                    all_orderable = False

                if best_ask is None:
                    all_asks_present = False
                else:
                    asks.append(float(best_ask))

                if best_bid is None:
                    all_bids_present = False
                else:
                    bids.append(float(best_bid))

                reference_prices.append(float(reference_price))

                legs.append({
                    "market_id": adapter._extract_market_id(m),
                    "name": (
                        m.get("question")
                        or m.get("title")
                        or m.get("slug")
                    ),
                    "group_item_title": (
                        m.get("groupItemTitle") or ""
                    ),
                    "active": active,
                    "closed": closed,
                    "archived": archived,
                    "accepting_orders": accepting_orders,
                    "orderable": orderable,
                    "reference_yes_price": reference_price,
                    "best_bid": best_bid,
                    "best_ask": best_ask,
                    "quote_state": quote.get("quote_state"),
                    "spread": quote.get("spread"),
                    "volume_total_usd": quote.get(
                        "volume_total_usd"
                    ),
                    "liquidity_usd": quote.get(
                        "liquidity_usd"
                    ),
                    "clob_token_ids": quote.get(
                        "clob_token_ids"
                    ),
                })

            required_leg_count = len(legs)

            reference_complete = (
                required_leg_count > 0
                and len(reference_prices) == required_leg_count
            )

            ask_complete = (
                required_leg_count > 0
                and all_orderable
                and all_asks_present
                and len(asks) == required_leg_count
            )

            bid_complete = (
                required_leg_count > 0
                and all_orderable
                and all_bids_present
                and len(bids) == required_leg_count
            )

            reference_sum = (
                sum(reference_prices)
                if reference_complete
                else None
            )

            ask_sum = (
                sum(asks)
                if ask_complete
                else None
            )

            bid_sum = (
                sum(bids)
                if bid_complete
                else None
            )

            gross_buy_all_yes_edge = (
                1.0 - ask_sum
                if ask_sum is not None
                else None
            )

            groups.append({
                "structural_group_version": "1.0",
                "observed_at": observed_at,
                "event_id": event_group_id,
                "title": title,
                "neg_risk": True,
                "neg_risk_augmented": False,
                "neg_risk_market_id": neg_risk_market_id,
                "structural_group_type": "STANDARD_NEGRISK",
                "structural_group_verified": (
                    bool(neg_risk_market_id)
                    and group_id_consistent
                    and required_leg_count >= 2
                ),
                "group_id_consistent": group_id_consistent,
                "required_leg_count": required_leg_count,
                "all_orderable": all_orderable,
                "reference_complete": reference_complete,
                "reference_sum": reference_sum,
                "ask_complete": ask_complete,
                "ask_sum": ask_sum,
                "gross_buy_all_yes_edge": gross_buy_all_yes_edge,
                "bid_complete": bid_complete,
                "bid_sum": bid_sum,

                # Deliberately false until:
                # - real CLOB depth is measured
                # - fees/costs are modeled
                # - multi-leg execution exists
                # - legging/partial-fill risk is controlled
                "execution_ready": False,

                "legs": legs,
            })

        return groups
