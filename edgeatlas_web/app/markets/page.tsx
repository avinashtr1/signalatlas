import Link from "next/link";

import {
  formatNumber,
  getMarkets,
  getSignalHealth,
  numberValue,
  objectValue,
  rowsFromResponse,
  safe,
  text,
} from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function MarketsPage() {
  const [result, signalResult] = await Promise.all([
    safe(() => getMarkets(250)),
    safe(getSignalHealth),
  ]);

  const markets = result.ok
    ? rowsFromResponse(result.data)
    : [];

  const signal = signalResult.ok
    ? signalResult.data
    : null;

  const measurement = objectValue(
    signal,
    "measurement"
  );

  const gamma = objectValue(
    measurement,
    "gamma"
  );

  const measuredTotal = numberValue(
    gamma,
    "latest_bucket_rows"
  );

  return (
    <div className="page">
      <header className="page-header">
        <div>
          <div className="eyebrow">SIGNALATLAS</div>
          <h1>Markets</h1>
          <p>
            Current measured market state. Coverage is the present partial
            active-event collector slice, not the complete Polymarket universe.
          </p>
        </div>
      </header>

      {!result.ok ? (
        <div className="error-box">
          SignalAtlas market API unavailable: {result.error}
        </div>
      ) : (
        <section className="panel">
          <div className="panel-title">
            {`Current Snapshot · Showing ${markets.length}${
              measuredTotal !== null
                ? ` of ${measuredTotal}`
                : ""
            } measured markets`}
          </div>

          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Market</th>
                  <th>Quote state</th>
                  <th>Bid</th>
                  <th>Ask</th>
                  <th>Mid</th>
                  <th>Spread</th>
                  <th>Volume</th>
                  <th>Liquidity</th>
                  <th>Observed</th>
                </tr>
              </thead>

              <tbody>
                {markets.map((m, i) => {
                  const marketId = text(m, "market_id", "id");

                  return (
                    <tr key={`${marketId}-${i}`}>
                      <td className="market-name">
                        <Link
                          className="market-link"
                          href={`/markets/${encodeURIComponent(marketId)}`}
                        >
                          {text(
                            m,
                            "market_name",
                            "question",
                            "title",
                            "slug",
                            "market_id"
                          )}
                        </Link>

                        <div className="market-meta">
                          ID {marketId} · {text(m, "structural_group_type")}
                        </div>
                      </td>

                      <td>
                        <span className="badge badge-muted">
                          {text(m, "quote_state")}
                        </span>
                      </td>

                      <td>{formatNumber(numberValue(m, "best_bid"))}</td>
                      <td>{formatNumber(numberValue(m, "best_ask"))}</td>
                      <td>{formatNumber(numberValue(m, "mid_price"))}</td>
                      <td>{formatNumber(numberValue(m, "spread"))}</td>

                      <td>{fmt(numberValue(m, "volume_total_usd"))}</td>
                      <td>{fmt(numberValue(m, "liquidity_usd"))}</td>

                      <td className="muted">
                        {text(m, "observation_bucket")}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {markets.length === 0 && (
            <div className="empty">No markets returned.</div>
          )}
        </section>
      )}
    </div>
  );
}

function fmt(n: number | null) {
  if (n === null) return "—";

  return new Intl.NumberFormat("en", {
    notation: "compact",
    maximumFractionDigits: 1,
  }).format(n);
}
