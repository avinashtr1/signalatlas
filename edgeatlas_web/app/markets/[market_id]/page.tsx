import Link from "next/link";

import {
  arrayValue,
  formatNumber,
  getForwardOutcomes,
  getMarket,
  getMeasurements,
  getOrderbook,
  numberValue,
  objectValue,
  safe,
  text,
  type JsonObject,
} from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function MarketDetailPage({
  params,
}: {
  params: Promise<{ market_id: string }>;
}) {
  const { market_id } = await params;
  const marketId = decodeURIComponent(market_id);

  const [marketResult, bookResult, measurementsResult, outcomesResult] =
    await Promise.all([
      safe(() => getMarket(marketId)),
      safe(() => getOrderbook(marketId)),
      safe(() => getMeasurements(marketId)),
      safe(() => getForwardOutcomes(marketId)),
    ]);

  const market = marketResult.ok
    ? objectValue(marketResult.data, "market")
    : null;

  const sourceScope = marketResult.ok
    ? objectValue(marketResult.data, "source_scope")
    : null;

  const tokenBooks = bookResult.ok
    ? arrayValue(bookResult.data, "token_books")
    : [];

  const measurements = measurementsResult.ok
    ? arrayValue(measurementsResult.data, "rows")
    : [];

  const outcomes = outcomesResult.ok
    ? arrayValue(outcomesResult.data, "rows")
    : [];

  if (!market) {
    return (
      <div className="page">
        <Link href="/markets" className="back-link">
          ← Markets
        </Link>

        <div className="error-box">
          Market {marketId} unavailable
          {marketResult.ok ? "." : `: ${marketResult.error}`}
        </div>
      </div>
    );
  }

  return (
    <div className="page">
      <Link href="/markets" className="back-link">
        ← Markets
      </Link>

      <header className="market-header">
        <div>
          <div className="eyebrow">
            MARKET {text(market, "market_id")}
          </div>

          <h1>{text(market, "market_name")}</h1>

          <div className="market-context">
            {text(market, "event_title")}
          </div>
        </div>

        <div className="header-badges">
          <span className="badge badge-muted">
            {text(market, "quote_state")}
          </span>

          <span className="badge badge-muted">
            {text(market, "structural_group_type")}
          </span>
        </div>
      </header>

      <section className="kpi-grid">
        <KPI
          label="Best Bid"
          value={price(numberValue(market, "best_bid"))}
          sub="Gamma current quote"
        />

        <KPI
          label="Best Ask"
          value={price(numberValue(market, "best_ask"))}
          sub="Gamma current quote"
        />

        <KPI
          label="Mid"
          value={price(numberValue(market, "mid_price"))}
          sub="Measured midpoint"
        />

        <KPI
          label="Spread"
          value={price(numberValue(market, "spread"))}
          sub="Top-of-book"
        />
      </section>

      <section className="grid-2">
        <Panel title="Market State">
          <Row label="Quote state" value={text(market, "quote_state")} />
          <Row
            label="Tradable top-of-book"
            value={text(market, "tradable_top_of_book")}
          />
          <Row
            label="Accepting orders"
            value={text(market, "accepting_orders")}
          />
          <Row label="Active" value={text(market, "active")} />
          <Row
            label="Resolution time valid"
            value={text(market, "resolution_time_valid")}
          />
          <Row
            label="Raw resolution time"
            value={text(market, "raw_resolution_time")}
          />
        </Panel>

        <Panel title="Market Structure">
          <Row
            label="Structural group"
            value={text(market, "structural_group_type")}
          />
          <Row label="NegRisk" value={text(market, "neg_risk")} />
          <Row
            label="NegRisk augmented"
            value={text(market, "neg_risk_augmented")}
          />
          <Row
            label="Volume"
            value={usd(numberValue(market, "volume_total_usd"))}
          />
          <Row
            label="Liquidity"
            value={usd(numberValue(market, "liquidity_usd"))}
          />
          <Row
            label="Observed"
            value={text(market, "observation_bucket")}
          />
        </Panel>
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <div className="panel-title">Real CLOB Execution Measurement</div>
            <div className="muted">
              Current executable-book measurements. These are execution
              diagnostics, not alpha estimates.
            </div>
          </div>

          {bookResult.ok ? (
            <span className="badge badge-good">CLOB AVAILABLE</span>
          ) : (
            <span className="badge badge-muted">NO CURRENT CLOB ROW</span>
          )}
        </div>

        {tokenBooks.length === 0 ? (
          <div className="empty">
            No current CLOB measurement is available for this market.
          </div>
        ) : (
          <div className="book-grid">
            {tokenBooks.map((book, i) => (
              <TokenBook
                key={`${text(book, "token_id")}-${i}`}
                book={book}
              />
            ))}
          </div>
        )}
      </section>

      <section className="panel">
        <div className="panel-title">
          Measurement History · {measurements.length} observations
        </div>

        {measurements.length === 0 ? (
          <div className="empty">No measurement history available.</div>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Bucket</th>
                  <th>State</th>
                  <th>Bid</th>
                  <th>Ask</th>
                  <th>Mid</th>
                  <th>Spread</th>
                  <th>Volume</th>
                  <th>Liquidity</th>
                </tr>
              </thead>

              <tbody>
                {measurements.map((row, i) => (
                  <tr key={`${text(row, "observation_bucket")}-${i}`}>
                    <td>{text(row, "observation_bucket")}</td>
                    <td>{text(row, "quote_state")}</td>
                    <td>{price(numberValue(row, "best_bid"))}</td>
                    <td>{price(numberValue(row, "best_ask"))}</td>
                    <td>{price(numberValue(row, "mid_price"))}</td>
                    <td>{price(numberValue(row, "spread"))}</td>
                    <td>{usd(numberValue(row, "volume_total_usd"))}</td>
                    <td>{usd(numberValue(row, "liquidity_usd"))}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <div className="panel-title">
              Forward Outcomes · {outcomes.length} labels
            </div>

            <div className="muted">
              Observed future market states used for research and calibration.
              They are descriptive labels, not trading signals.
            </div>
          </div>
        </div>

        {outcomes.length === 0 ? (
          <div className="empty">
            No matured forward outcomes yet for this market.
          </div>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Horizon</th>
                  <th>Base</th>
                  <th>Target</th>
                  <th>Status</th>
                  <th>Base Mid</th>
                  <th>Future Mid</th>
                  <th>Δ Mid</th>
                  <th>Base Spread</th>
                  <th>Future Spread</th>
                  <th>Timing Error</th>
                </tr>
              </thead>

              <tbody>
                {outcomes.map((row, i) => {
                  const base = numberValue(row, "base_mid_price");
                  const future = numberValue(row, "future_mid_price");

                  const delta =
                    base !== null && future !== null
                      ? future - base
                      : null;

                  return (
                    <tr
                      key={`${text(row, "base_observation_bucket")}-${text(
                        row,
                        "horizon_minutes"
                      )}-${i}`}
                    >
                      <td>
                        {text(row, "horizon_minutes")}m
                      </td>

                      <td>{text(row, "base_observation_bucket")}</td>
                      <td>{text(row, "target_bucket")}</td>
                      <td>{text(row, "label_status")}</td>
                      <td>{price(base)}</td>
                      <td>{price(future)}</td>

                      <td className={deltaTone(delta)}>
                        {signedPrice(delta)}
                      </td>

                      <td>
                        {price(numberValue(row, "base_spread"))}
                      </td>

                      <td>
                        {price(numberValue(row, "future_spread"))}
                      </td>

                      <td>
                        {seconds(
                          numberValue(row, "horizon_error_seconds")
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="panel">
        <div className="panel-title">Source Semantics</div>

        <Row
          label="Collector coverage"
          value={text(sourceScope, "coverage")}
        />

        <Row
          label="Complete universe"
          value={text(sourceScope, "complete_universe")}
        />

        <Row
          label="Source note"
          value={text(sourceScope, "note")}
        />

        <Row
          label="Market source"
          value={text(market, "source")}
        />

        <Row
          label="Schema"
          value={text(market, "schema_version")}
        />
      </section>
    </div>
  );
}

function TokenBook({ book }: { book: JsonObject }) {
  return (
    <div className="token-book">
      <div className="token-book-header">
        <div>
          <div className="token-side">
            {text(book, "outcome_side")}
          </div>

          <div className="token-id">
            token {shortToken(text(book, "token_id"))}
          </div>
        </div>

        <span className="badge badge-good">
          {text(book, "collection_status")}
        </span>
      </div>

      <div className="book-top">
        <Metric
          label="Bid"
          value={price(numberValue(book, "best_bid"))}
        />
        <Metric
          label="Ask"
          value={price(numberValue(book, "best_ask"))}
        />
        <Metric
          label="Spread"
          value={price(numberValue(book, "spread"))}
        />
      </div>

      <div className="subsection-title">Top Level</div>

      <Row
        label="Top bid size"
        value={shares(numberValue(book, "top_bid_size"))}
      />
      <Row
        label="Top ask size"
        value={shares(numberValue(book, "top_ask_size"))}
      />
      <Row
        label="Bid levels"
        value={text(book, "bid_levels")}
      />
      <Row
        label="Ask levels"
        value={text(book, "ask_levels")}
      />

      <div className="subsection-title">Depth</div>

      <DepthRow
        label="Within 1¢"
        bid={numberValue(book, "bid_depth_1c_usd")}
        ask={numberValue(book, "ask_depth_1c_usd")}
      />

      <DepthRow
        label="Within 2¢"
        bid={numberValue(book, "bid_depth_2c_usd")}
        ask={numberValue(book, "ask_depth_2c_usd")}
      />

      <DepthRow
        label="Within 5¢"
        bid={numberValue(book, "bid_depth_5c_usd")}
        ask={numberValue(book, "ask_depth_5c_usd")}
      />

      <div className="subsection-title">Execution Simulation</div>

      <ExecutionRow
        size="$10"
        buyVwap={numberValue(book, "buy_vwap_10")}
        buyFill={numberValue(book, "buy_fill_10")}
        sellVwap={numberValue(book, "sell_vwap_10")}
        sellFill={numberValue(book, "sell_fill_10")}
      />

      <ExecutionRow
        size="$50"
        buyVwap={numberValue(book, "buy_vwap_50")}
        buyFill={numberValue(book, "buy_fill_50")}
        sellVwap={numberValue(book, "sell_vwap_50")}
        sellFill={numberValue(book, "sell_fill_50")}
      />

      <ExecutionRow
        size="$100"
        buyVwap={numberValue(book, "buy_vwap_100")}
        buyFill={numberValue(book, "buy_fill_100")}
        sellVwap={numberValue(book, "sell_vwap_100")}
        sellFill={numberValue(book, "sell_fill_100")}
      />
    </div>
  );
}

function ExecutionRow({
  size,
  buyVwap,
  buyFill,
  sellVwap,
  sellFill,
}: {
  size: string;
  buyVwap: number | null;
  buyFill: number | null;
  sellVwap: number | null;
  sellFill: number | null;
}) {
  return (
    <div className="execution-row">
      <strong>{size}</strong>

      <span>
        BUY {price(buyVwap)}
        <small>{fillLabel(buyFill)}</small>
      </span>

      <span>
        SELL {price(sellVwap)}
        <small>{fillLabel(sellFill)}</small>
      </span>
    </div>
  );
}

function DepthRow({
  label,
  bid,
  ask,
}: {
  label: string;
  bid: number | null;
  ask: number | null;
}) {
  return (
    <div className="depth-row">
      <span>{label}</span>
      <strong>BID {usd(bid)}</strong>
      <strong>ASK {usd(ask)}</strong>
    </div>
  );
}

function KPI({
  label,
  value,
  sub,
}: {
  label: string;
  value: string;
  sub: string;
}) {
  return (
    <div className="kpi">
      <div className="kpi-label">{label}</div>
      <div className="kpi-value">{value}</div>
      <div className="kpi-sub">{sub}</div>
    </div>
  );
}

function Panel({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="panel">
      <div className="panel-title">{title}</div>
      {children}
    </div>
  );
}

function Row({
  label,
  value,
}: {
  label: string;
  value: string;
}) {
  return (
    <div className="metric-row">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function Metric({
  label,
  value,
}: {
  label: string;
  value: string;
}) {
  return (
    <div>
      <div className="mini-label">{label}</div>
      <div className="mini-value">{value}</div>
    </div>
  );
}

function price(n: number | null) {
  return n === null ? "—" : n.toFixed(4);
}

function signedPrice(n: number | null) {
  if (n === null) return "—";
  return `${n > 0 ? "+" : ""}${n.toFixed(4)}`;
}

function deltaTone(n: number | null) {
  if (n === null || n === 0) return "muted";
  return n > 0 ? "tone-good" : "tone-bad";
}

function usd(n: number | null) {
  if (n === null) return "—";

  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 2,
  }).format(n);
}

function shares(n: number | null) {
  if (n === null) return "—";
  return `${n.toFixed(2)} shares`;
}

function seconds(n: number | null) {
  if (n === null) return "—";
  return `${n.toFixed(1)}s`;
}

function fillLabel(n: number | null) {
  if (n === null) return " · fill —";
  return ` · fill ${n.toFixed(2)}`;
}

function shortToken(v: string) {
  if (!v || v === "—") return "—";
  if (v.length <= 14) return v;

  return `${v.slice(0, 7)}…${v.slice(-5)}`;
}
