class BasketBuilder:
    """
    Build executable arbitrage baskets from accepted candidates.

    Supported:
    - bucket_member groups: if sum(YES prices) != 1, trade whole group same side
    """

    def build_baskets(self, acceptable_candidates):
        baskets = []
        used = set()

        # build bucket baskets first
        by_bucket = {}
        for result in acceptable_candidates:
            c = result["candidate"]
            details = c.signal_details or {}
            bucket_id = details.get("bucket_group_id")
            relation_type = details.get("relation_type")
            if relation_type == "bucket_member" and bucket_id:
                by_bucket.setdefault(bucket_id, []).append(result)

        for bucket_id, results in by_bucket.items():
            if len(results) < 2:
                continue

            basket = []
            side = results[0]["analysis"].get("trade_side", "LONG")

            for r in results:
                rid = r["candidate"].candidate_id
                if rid in used:
                    continue
                rr = dict(r)
                rr["analysis"] = dict(r["analysis"])
                rr["analysis"]["trade_side"] = side
                basket.append(rr)
                used.add(rid)

            if len(basket) >= 2:
                baskets.append(basket)

        return baskets
