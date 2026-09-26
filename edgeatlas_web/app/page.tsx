import {
  formatNumber,
  getMarkets,
  getSignalHealth,
  getVelocityHealth,
  numberValue,
  objectValue,
  rowsFromResponse,
  safe,
  text,
} from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function TerminalPage() {
  const [signalResult, marketsResult, velocityResult] = await Promise.all([
    safe(getSignalHealth),
    safe(() => getMarkets(100)),
    safe(getVelocityHealth),
  ]);

  const markets = marketsResult.ok
    ? rowsFromResponse(marketsResult.data)
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

  const twoSided = markets.filter(
    (m) => text(m, "quote_state") === "TWO_SIDED"
  ).length;

  const oneSided = markets.filter(
    (m) => text(m, "quote_state") === "ONE_SIDED"
  ).length;

  const noBook = markets.filter(
    (m) => text(m, "quote_state") === "NO_BOOK"
  ).length;

  return (
    <div className="page">
      <header className="page-header">
        <div>
          <div className="eyebrow">SYSTEM TERMINAL</div>
          <h1>EdgeAtlas</h1>
          <p>
            Measurement-first prediction-market infrastructure with
            SignalAtlas intelligence and isolated VelocityAtlas execution.
          </p>
        </div>

        <div className="status-line">
          <StatusDot ok={signalResult.ok} />
          SignalAtlas
          <StatusDot ok={velocityResult.ok} />
          VelocityAtlas
        </div>
      </header>

      <section className="kpi-grid">
        <KPI
          label="Markets shown"
          value={
            measuredTotal !== null
              ? `${markets.length} / ${measuredTotal}`
              : String(markets.length)
          }
          sub="Displayed / latest measured bucket · partial event slice"
        />
        <KPI
          label="Two-sided books"
          value={String(twoSided)}
          sub="Measured executable quote state"
        />
        <KPI
          label="One-sided books"
          value={String(oneSided)}
          sub="Incomplete top-of-book"
        />
        <KPI
          label="No book"
          value={String(noBook)}
          sub="No usable current quote"
        />
      </section>

      <section className="grid-2">
        <Panel title="Intelligence State">
          <Row
            label="Measurement API"
            value={signalResult.ok ? "ONLINE" : "UNAVAILABLE"}
            tone={signalResult.ok ? "good" : "bad"}
          />
          <Row label="Universe coverage" value="PARTIAL EVENT SLICE" />
          <Row label="Brain" value="FAIL-CLOSED" tone="warn" />
          <Row label="Directional alpha" value="UNCALIBRATED" tone="warn" />
          <Row label="Execution authority" value="CLOB" />
        </Panel>

        <Panel title="Execution State">
          <Row
            label="Velocity API"
            value={velocityResult.ok ? "ONLINE" : "UNAVAILABLE"}
            tone={velocityResult.ok ? "good" : "bad"}
          />
          <Row label="API exposure" value="LOCALHOST ONLY" tone="good" />
          <Row label="Live 5m service" value="DISABLED / UNFUNDED" />
          <Row label="Credential state" value="ROTATION REQUIRED BEFORE LIVE" tone="warn" />
          <Row label="Mode" value="OBSERVE / RESEARCH" />
        </Panel>
      </section>

      <section className="panel">
        <div className="panel-title">Current Market Measurements</div>

        {markets.length === 0 ? (
          <div className="empty">
            {marketsResult.ok
              ? "No markets returned by the current collector scope."
              : `SignalAtlas markets unavailable: ${marketsResult.error}`}
          </div>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Market</th>
                  <th>State</th>
                  <th>Bid</th>
                  <th>Ask</th>
                  <th>Spread</th>
                  <th>Volume</th>
                </tr>
              </thead>
              <tbody>
                {markets.slice(0, 12).map((m, i) => (
                  <tr key={`${text(m, "market_id", "id")}-${i}`}>
                    <td className="market-name">
                      {text(m, "question", "title", "market_name", "slug", "market_id")}
                    </td>
                    <td>
                      <Badge value={text(m, "quote_state")} />
                    </td>
                    <td>{formatNumber(numberValue(m, "best_bid", "bid"))}</td>
                    <td>{formatNumber(numberValue(m, "best_ask", "ask"))}</td>
                    <td>{formatNumber(numberValue(m, "spread"))}</td>
                    <td>{formatCompact(numberValue(m, "volume"))}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}

function StatusDot({ ok }: { ok: boolean }) {
  return <span className={`dot ${ok ? "dot-good" : "dot-bad"}`} />;
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
  tone,
}: {
  label: string;
  value: string;
  tone?: "good" | "warn" | "bad";
}) {
  return (
    <div className="metric-row">
      <span>{label}</span>
      <strong className={tone ? `tone-${tone}` : ""}>{value}</strong>
    </div>
  );
}

function Badge({ value }: { value: string }) {
  const normalized = value.toUpperCase();
  const tone =
    normalized === "TWO_SIDED"
      ? "good"
      : normalized === "ONE_SIDED"
        ? "warn"
        : "muted";

  return <span className={`badge badge-${tone}`}>{value}</span>;
}

function formatCompact(n: number | null) {
  if (n === null) return "—";
  return new Intl.NumberFormat("en", {
    notation: "compact",
    maximumFractionDigits: 1,
  }).format(n);
}
