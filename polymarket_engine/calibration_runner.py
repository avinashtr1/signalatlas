import json, collections, random
from datetime import datetime, timezone, timedelta
from .models.trigger_event import TriggerEvent
from .triggers.signal_listener import SignalListener
from .triggers.market_mapper import MarketMapper
from .brain.evaluate import BrainEvaluator
from .config.market_filters import MarketFilterConfig
from .execution.paper_executor import PaperExecutor
from .execution.resolution_watcher import ResolutionWatcher
from .execution.capital_allocator import CapitalAllocator
from polymarket_engine.brain.inventory import Inventory
from polymarket_engine.brain.gates import Gates


class PerformanceEvaluationFixtures:

    def __init__(self):
        self.cycle_num = 0
        now = datetime.now(timezone.utc)
        self.market_data = {}
        self._build_structured_market_universe(now)

    def _clamp_prob(self, x):
        return max(0.02, min(0.98, x))

    def _add_market(
        self,
        market_id,
        name,
        end_time,
        current_price,
        volume,
        market_type,
        event_group,
        relation_type="standalone",
        parent_market_id=None,
        complement_market_id=None,
        latent_true_prob=None,
        mispricing_tag=None,
    ):
        self.market_data[market_id] = {
            "market_id": market_id,
            "name": name,
            "end_time": end_time.isoformat(),
            "current_price": self._clamp_prob(current_price),
            "liquidity_snapshot": {"volume_usd": volume},
            "truth_source": "Sim",
            "truth_source_confidence": random.uniform(0.70, 0.95),
            "objective_support": True,
            "market_type": market_type,
            "event_group": event_group,
            "relation_type": relation_type,
            "parent_market_id": parent_market_id,
            "complement_market_id": complement_market_id,
            "latent_true_prob": latent_true_prob if latent_true_prob is not None else current_price,
            "mispricing_tag": mispricing_tag,
        }

    def _build_structured_market_universe(self, now):
        groups = [
            ("BTC_PRICE", "crypto"),
            ("ETH_PRICE", "crypto"),
            ("SOL_PRICE", "crypto"),
            ("POLITICS", "event"),
            ("MACRO", "event"),
        ]

        idx = 0

        for event_group, market_type in groups:
            base_true = random.uniform(0.35, 0.65)
            days = random.randint(5, 30)
            end_time = now + timedelta(days=days)

            parent_market_id = f"0x{idx}"
            parent_market_price = self._clamp_prob(base_true + random.uniform(-0.04, 0.04))
            parent_volume = random.randint(220000, 650000)

            self._add_market(
                market_id=parent_market_id,
                name=f"{event_group} Parent",
                end_time=end_time,
                current_price=parent_market_price,
                volume=parent_volume,
                market_type=market_type,
                event_group=event_group,
                relation_type="parent",
                latent_true_prob=base_true,
            )
            idx += 1

            # Child A: often fair, sometimes badly overpriced
            child1_true = self._clamp_prob(base_true - random.uniform(0.06, 0.18))
            child1_market_price = self._clamp_prob(child1_true + random.uniform(-0.03, 0.04))
            child1_volume = random.randint(50000, 180000)
            child1_tag = "normal"

            if random.random() < 0.55:
                child1_market_price = self._clamp_prob(parent_market_price + random.uniform(0.06, 0.16))
                child1_volume = random.randint(15000, 80000)
                child1_tag = "child_overpriced"

            self._add_market(
                market_id=f"0x{idx}",
                name=f"{event_group} Child A",
                end_time=end_time,
                current_price=child1_market_price,
                volume=child1_volume,
                market_type=market_type,
                event_group=event_group,
                relation_type="child",
                parent_market_id=parent_market_id,
                latent_true_prob=child1_true,
                mispricing_tag=child1_tag,
            )
            idx += 1

            # Child B: another chance for strong violation
            child2_true = self._clamp_prob(base_true - random.uniform(0.04, 0.15))
            child2_market_price = self._clamp_prob(child2_true + random.uniform(-0.03, 0.04))
            child2_volume = random.randint(50000, 180000)
            child2_tag = "normal"

            if random.random() < 0.45:
                child2_market_price = self._clamp_prob(parent_market_price + random.uniform(0.05, 0.14))
                child2_volume = random.randint(20000, 90000)
                child2_tag = "child_overpriced"

            self._add_market(
                market_id=f"0x{idx}",
                name=f"{event_group} Child B",
                end_time=end_time,
                current_price=child2_market_price,
                volume=child2_volume,
                market_type=market_type,
                event_group=event_group,
                relation_type="child",
                parent_market_id=parent_market_id,
                latent_true_prob=child2_true,
                mispricing_tag=child2_tag,
            )
            idx += 1

            # Complement markets
            yes_true = self._clamp_prob(base_true + random.uniform(-0.03, 0.03))
            no_true = self._clamp_prob(1.0 - yes_true)

            yes_price = self._clamp_prob(yes_true + random.uniform(-0.03, 0.03))
            no_price = self._clamp_prob(no_true + random.uniform(-0.03, 0.03))

            yes_volume = random.randint(70000, 220000)
            no_volume = random.randint(70000, 220000)
            yes_tag = "normal"
            no_tag = "normal"

            # inject stronger complement inconsistency
            if random.random() < 0.60:
                drift = random.uniform(0.08, 0.18)
                yes_price = self._clamp_prob(yes_price + drift)
                yes_volume = random.randint(15000, 90000)
                no_volume = random.randint(15000, 90000)
                yes_tag = "complement_dislocation"
                no_tag = "complement_dislocation"

            yes_id = f"0x{idx}"
            no_id = f"0x{idx+1}"

            self._add_market(
                market_id=yes_id,
                name=f"{event_group} YES",
                end_time=end_time,
                current_price=yes_price,
                volume=yes_volume,
                market_type=market_type,
                event_group=event_group,
                relation_type="complement_yes",
                complement_market_id=no_id,
                latent_true_prob=yes_true,
                mispricing_tag=yes_tag,
            )

            self._add_market(
                market_id=no_id,
                name=f"{event_group} NO",
                end_time=end_time,
                current_price=no_price,
                volume=no_volume,
                market_type=market_type,
                event_group=event_group,
                relation_type="complement_no",
                complement_market_id=yes_id,
                latent_true_prob=no_true,
                mispricing_tag=no_tag,
            )
            idx += 2

    def listen_for_signals(self):
        self.cycle_num += 1
        now = datetime.now(timezone.utc)

        if self.cycle_num % 5 == 0:
            return [
                TriggerEvent(
                    "price_momentum_burst",
                    "Binance",
                    "BTC",
                    now,
                    {"change": random.uniform(250, 900)}
                )
            ]

        return []

    def get_markets_for_trigger(self, trigger_event):
        return list(self.market_data.values())

    def get_outcome_source(self):
        outcomes = {}

        for m in self.market_data.values():
            latent_true_prob = m.get("latent_true_prob", m["current_price"])
            tag = m.get("mispricing_tag", "normal")

            # mispriced contracts snap back harder toward latent truth
            if tag in ["child_overpriced", "complement_dislocation"]:
                outcome_price = self._clamp_prob(latent_true_prob + random.uniform(-0.015, 0.015))
            else:
                outcome_price = self._clamp_prob(latent_true_prob + random.uniform(-0.03, 0.03))

            outcomes[m["market_id"]] = {
                "outcome_price": outcome_price,
                "status": "RESOLVED"
            }

        return outcomes


def run_single_experiment(name: str, config: dict, cycles: int) -> dict:
    random.seed(hash(name) & 0xffffffff)

    inventory = Inventory(total_capital=100000.0)
    paper_executor = PaperExecutor()
    fixtures = PerformanceEvaluationFixtures()
    resolution_watcher = ResolutionWatcher(paper_executor, inventory, fixtures.get_outcome_source())
    allocator_instance = CapitalAllocator(inventory, paper_executor, config)
    filter_config = MarketFilterConfig()
    gates_instance = Gates()
    brain_evaluator = BrainEvaluator(filter_config, gates_instance, inventory)
    market_mapper = MarketMapper(filter_config)
    market_mapper.polymarket_adapter = fixtures

    triggers_seen = 0
    markets_returned = 0
    candidates_mapped = 0
    brain_accepts = 0
    brain_rejects = 0
    allocator_ranked = 0
    peak_locked_capital = 0

    for _ in range(cycles):
        triggers = fixtures.listen_for_signals()
        if not triggers:
            continue

        triggers_seen += len(triggers)

        for trigger in triggers:
            markets = market_mapper.polymarket_adapter.get_markets_for_trigger(trigger)
            markets_returned += len(markets)

            candidates = market_mapper.map_trigger_to_candidates(trigger)
            candidates_mapped += len(candidates)

            acceptable_candidates = []

            for candidate in candidates:
                decision = brain_evaluator.evaluate_candidate(candidate)

                if decision["decision"] == "ACCEPT":
                    brain_accepts += 1
                    acceptable_candidates.append(decision)
                else:
                    brain_rejects += 1

            if acceptable_candidates:
                report = allocator_instance.allocate(acceptable_candidates)
                allocator_ranked += report.get("candidates_ranked", 0)

        peak_locked_capital = max(peak_locked_capital, inventory.locked_capital_total)

    resolution_watcher.check_and_settle_positions()
    final_summary = inventory.get_summary(paper_executor)

    realized_pnl = final_summary.get("pnl_state", {}).get("realized_pnl", 0.0)
    open_positions_count = final_summary.get("position_state", {}).get("open_positions_count", 0)
    closed_positions_count = final_summary.get("position_state", {}).get("closed_positions_count", 0)

    funded_count = open_positions_count + closed_positions_count
    pnl_per_funded_trade = (realized_pnl / funded_count) if funded_count > 0 else 0.0
    pnl_per_peak_capital = (realized_pnl / peak_locked_capital) if peak_locked_capital > 0 else 0.0

    return {
        "Experiment": name,
        "config": config,
        "triggers_seen": triggers_seen,
        "markets_returned": markets_returned,
        "candidates_mapped": candidates_mapped,
        "brain_accepts": brain_accepts,
        "brain_rejects": brain_rejects,
        "allocator_ranked": allocator_ranked,
        "cycles": cycles,
        "Total Realized PnL": realized_pnl,
        "PnL per Funded Trade": pnl_per_funded_trade,
        "Peak Locked Capital": peak_locked_capital,
        "PnL / Peak Locked Capital": pnl_per_peak_capital,
        "Funded Count": funded_count,
        "Open Positions": open_positions_count,
        "Closed Positions": closed_positions_count,
        "Fill Mix": funded_count,
    }


if __name__ == "__main__":
    cfg = {
        "W_ANNUALIZED_EDGE": 0.3,
        "W_FILL_PROB": 0.2,
        "W_NET_EDGE": 0.5,
        "DS_BASE_RISK_PCT": 0.06,
        "DS_SCORE_SENSITIVITY": 0.02,
    }

    for name, cy in [("CHECK_200", 200), ("CHECK_1000", 1000)]:
        r = run_single_experiment(name, cfg, cy)
        print(name, r["Total Realized PnL"], r["PnL / Peak Locked Capital"], r["Funded Count"])
