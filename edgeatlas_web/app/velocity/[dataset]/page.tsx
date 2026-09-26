import Link from "next/link";
import { notFound } from "next/navigation";

import {
  arrayValue,
  getVelocityDataset,
  numberValue,
  objectValue,
  safe,
  text,
  value,
  type JsonObject,
} from "@/lib/api";

export const dynamic = "force-dynamic";

const DATASETS = {
  "live-log": {
    title: "Historical Live Log",
    endpoint: "/live",
    listKey: "closed_trades",
    mode: "HISTORICAL LIVE",
    note:
      "Locally-recorded historical live trades. Current exchange balance and positions are intentionally disabled until credential rotation.",
  },

  "paper-15m": {
    title: "Paper 15m",
    endpoint: "/data",
    listKey: "closed_trades",
    mode: "PAPER",
    note:
      "Dedicated 15-minute paper trading ledger. Results are simulated and must not be interpreted as exchange performance.",
  },

  "recorded-5m": {
    title: "5m Live-Mode Ledger",
    endpoint: "/data5m",
    listKey: "closed_trades",
    mode: "RECORDED LIVE-MODE",
    note:
      "Rows are marked mode=LIVE. The legacy /dry5m endpoint points to these exact same files, so it is not presented as an independent dataset.",
  },

  "dry-15m": {
    title: "Dry 15m",
    endpoint: "/dry15m",
    listKey: "closed_trades",
    mode: "DRY RUN",
    note:
      "Dedicated dry-run ledger. Settled PnL and provisional snapshot PnL have different semantics and are kept separate.",
  },

  "activity-reconciliation": {
    title: "Activity Reconciliation",
    endpoint: "/truth5m",
    listKey: "trades",
    mode: "RECONCILIATION",
    note:
      "Reconstructed from Polymarket Activity API data. BUYs are size-filtered and exits are heuristically matched to REDEEM or SELL events. This is not an authoritative exchange ledger.",
  },
} as const;

type DatasetName = keyof typeof DATASETS;

export default async function VelocityDatasetPage({
  params,
}: {
  params: Promise<{ dataset: string }>;
}) {
  const { dataset } = await params;

  const config = DATASETS[dataset as DatasetName];

  if (!config) {
    notFound();
  }

  const result = await safe(() =>
    getVelocityDataset(config.endpoint)
  );

  const data = result.ok ? result.data : null;

  const rows =
    data === null
      ? []
      : arrayValue(data, config.listKey).slice(0, 100);

  const openTrades =
    data === null
      ? []
      : arrayValue(data, "open_trades");

  const exchange =
    data === null
      ? null
      : objectValue(data, "exchange");

  return (
    <div className="page">
      <Link href="/velocity" className="back-link">
        ← Velocity
      </Link>

      <header className="page-header">
        <div>
          <div className="eyebrow">VELOCITYATLAS · {config.mode}</div>
          <h1>{config.title}</h1>
          <p>{config.note}</p>
        </div>

        <span className="badge badge-muted">
          {config.mode}
        </span>
      </header>

      {!result.ok ? (
        <div className="error-box">
          Velocity endpoint unavailable: {result.error}
        </div>
      ) : (
        <>
          <section className="kpi-grid">
            <KPI
              label="Total PnL"
              value={money(
                numberValue(
                  data,
                  "total_pnl",
                  "settled_pnl"
                )
              )}
              sub={pnlSubtitle(dataset)}
            />

            <KPI
              label="Closed / Trades"
              value={countLabel(data, config.listKey)}
              sub="Source ledger count"
            />

            <KPI
              label="Open"
              value={String(
                numberValue(data, "open") ??
                  openTrades.length
              )}
              sub="Currently unresolved in dataset"
            />

            <KPI
              label="Win Rate"
              value={percent(numberValue(data, "win_rate"))}
              sub="Shown only when endpoint defines it"
            />
          </section>

          {dataset === "dry-15m" && (
            <section className="grid-2">
              <Panel title="Settled Accounting">
                <Row
                  label="Settled PnL"
                  value={money(
                    numberValue(data, "settled_pnl")
                  )}
                />
                <Row
                  label="Settled trades"
                  value={text(data, "settled_trade_count")}
                />
                <Row
                  label="Pending trades"
                  value={text(data, "pending_trade_count")}
                />
              </Panel>

              <Panel title="Provisional Snapshot Accounting">
                <Row
                  label="Provisional PnL"
                  value={money(
                    numberValue(data, "provisional_pnl")
                  )}
                />
                <Row
                  label="Provisional trades"
                  value={text(data, "provisional_trade_count")}
                />
                <Row
                  label="Provisional wins"
                  value={text(data, "provisional_win_count")}
                />
                <Row
                  label="Provisional losses"
                  value={text(data, "provisional_loss_count")}
                />
              </Panel>
            </section>
          )}

          {dataset === "activity-reconciliation" && (
            <section className="grid-2">
              <Panel title="Reconciliation Summary">
                <Row label="Wins" value={text(data, "wins")} />
                <Row label="Losses" value={text(data, "losses")} />
                <Row
                  label="Average win"
                  value={money(numberValue(data, "avg_win"))}
                />
                <Row
                  label="Average loss"
                  value={money(numberValue(data, "avg_loss"))}
                />
                <Row
                  label="Breakeven WR"
                  value={percent(
                    numberValue(data, "breakeven_wr")
                  )}
                />
              </Panel>

              <Panel title="Capital Reconstruction">
                <Row
                  label="Total spent"
                  value={money(
                    numberValue(data, "total_spent")
                  )}
                />
                <Row
                  label="Total redeemed"
                  value={money(
                    numberValue(data, "total_redeemed")
                  )}
                />
                <Row
                  label="Method"
                  value="Activity API reconstruction"
                />
                <Row
                  label="Authority"
                  value="RECONCILIATION ONLY"
                />
              </Panel>
            </section>
          )}

          {dataset === "live-log" && (
            <section className="panel">
              <div className="panel-title">
                Exchange Snapshot State
              </div>

              <Row
                label="Status"
                value={text(exchange, "status")}
              />
              <Row
                label="Reason"
                value={text(exchange, "reason")}
              />
            </section>
          )}

          <section className="panel">
            <div className="panel-heading">
              <div>
                <div className="panel-title">
                  Recent Records · showing {rows.length}
                </div>

                <div className="muted">
                  The UI intentionally caps rendered history at 100 rows.
                </div>
              </div>
            </div>

            {rows.length === 0 ? (
              <div className="empty">
                No records returned by this dataset.
              </div>
            ) : (
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Time</th>
                      <th>Market</th>
                      <th>Side</th>
                      <th>Entry</th>
                      <th>Exit</th>
                      <th>PnL</th>
                      <th>Status</th>
                    </tr>
                  </thead>

                  <tbody>
                    {rows.map((row, i) => (
                      <TradeRow
                        row={row}
                        key={`${rowKey(row)}-${i}`}
                      />
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </>
      )}
    </div>
  );
}

function TradeRow({ row }: { row: JsonObject }) {
  const pnl = numberValue(row, "realized_pnl", "pnl");

  return (
    <tr>
      <td className="muted">
        {formatTime(
          value(
            row,
            "closed_at",
            "settled_at",
            "timestamp",
            "opened_at"
          )
        )}
      </td>

      <td className="market-name">
        {text(row, "title", "slug", "market_id")}
      </td>

      <td>
        {text(
          row,
          "direction",
          "outcome",
          "token_side"
        )}
      </td>

      <td>
        {price(
          numberValue(
            row,
            "fill_price",
            "entry_yes_price",
            "entry_price"
          )
        )}
      </td>

      <td>
        {price(
          numberValue(
            row,
            "exit_yes_price",
            "final_yes_price",
            "forced_exit_price"
          )
        )}
      </td>

      <td className={pnlTone(pnl)}>
        {money(pnl)}
      </td>

      <td>
        {text(
          row,
          "result",
          "final_settlement_status",
          "close_reason",
          "status"
        )}
      </td>
    </tr>
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

function countLabel(
  data: JsonObject | null,
  listKey: string
) {
  if (!data) return "0";

  const explicit = numberValue(
    data,
    "closed_trade_count",
    "total_trades"
  );

  if (explicit !== null) return String(explicit);

  return String(arrayValue(data, listKey).length);
}

function pnlSubtitle(dataset: string) {
  if (dataset === "paper-15m") return "Simulated paper result";
  if (dataset === "dry-15m") return "Final-settlement result";
  if (dataset === "activity-reconciliation")
    return "Reconstructed resolved result";
  if (dataset === "live-log")
    return "Historical local live log";
  return "Recorded ledger result";
}

function money(n: number | null) {
  if (n === null) return "—";

  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 2,
  }).format(n);
}

function percent(n: number | null) {
  return n === null ? "—" : `${n.toFixed(1)}%`;
}

function price(n: number | null) {
  return n === null ? "—" : n.toFixed(4);
}

function pnlTone(n: number | null) {
  if (n === null || n === 0) return "muted";
  return n > 0 ? "tone-good" : "tone-bad";
}

function rowKey(row: JsonObject) {
  return text(
    row,
    "trade_id",
    "tx",
    "market_id",
    "timestamp"
  );
}

function formatTime(v: unknown) {
  if (typeof v === "number") {
    return new Date(v * 1000).toISOString();
  }

  if (typeof v === "string" && v) {
    const numeric = Number(v);

    if (
      Number.isFinite(numeric) &&
      /^\d+$/.test(v)
    ) {
      return new Date(numeric * 1000).toISOString();
    }

    return v;
  }

  return "—";
}
