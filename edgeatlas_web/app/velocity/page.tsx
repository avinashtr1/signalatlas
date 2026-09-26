import Link from "next/link";

import {
  getVelocityHealth,
  objectValue,
  safe,
  text,
} from "@/lib/api";

export const dynamic = "force-dynamic";

const datasets = [
  {
    href: "/velocity/live-log",
    title: "Historical Live Log",
    tag: "LIVE HISTORY",
    description:
      "Historical locally-recorded live trades. Exchange portfolio snapshot is disabled until credential rotation.",
  },
  {
    href: "/velocity/paper-15m",
    title: "Paper 15m",
    tag: "PAPER",
    description:
      "15-minute paper trading ledger from the dedicated paper trade files.",
  },
  {
    href: "/velocity/recorded-5m",
    title: "5m Live-Mode Ledger",
    tag: "RECORDED",
    description:
      "Recorded 5-minute ledger whose rows are marked mode=LIVE. The legacy /dry5m route aliases this exact dataset.",
  },
  {
    href: "/velocity/dry-15m",
    title: "Dry 15m",
    tag: "DRY RUN",
    description:
      "Dedicated 15-minute dry-run dataset with settled and provisional accounting.",
  },
  {
    href: "/velocity/activity-reconciliation",
    title: "Activity Reconciliation",
    tag: "RECONCILIATION",
    description:
      "Polymarket Activity API reconstruction using filtered BUYs and heuristic REDEEM/SELL matching. Not an authoritative exchange ledger.",
  },
];

export default async function VelocityPage() {
  const healthResult = await safe(getVelocityHealth);

  const health = healthResult.ok ? healthResult.data : null;
  const processes = objectValue(health, "processes");
  const cycles = objectValue(health, "last_cycle");
  const vol = objectValue(health, "vol");
  const kill = objectValue(health, "kill_switch");

  return (
    <div className="page">
      <header className="page-header">
        <div>
          <div className="eyebrow">VELOCITYATLAS</div>
          <h1>Execution</h1>
          <p>
            Operational and historical execution surfaces. Live, paper,
            dry-run and reconciliation datasets are intentionally kept
            semantically separate.
          </p>
        </div>

        <span
          className={`badge ${
            healthResult.ok ? "badge-good" : "badge-bad"
          }`}
        >
          {healthResult.ok ? "API ONLINE" : "API UNAVAILABLE"}
        </span>
      </header>

      <section className="dataset-grid">
        {datasets.map((dataset) => (
          <Link
            href={dataset.href}
            className="dataset-card"
            key={dataset.href}
          >
            <div className="dataset-tag">{dataset.tag}</div>
            <div className="dataset-title">{dataset.title}</div>
            <p>{dataset.description}</p>
            <div className="dataset-open">Open dataset →</div>
          </Link>
        ))}
      </section>

      <section className="grid-2">
        <Panel title="Process State">
          {!healthResult.ok ? (
            <div className="error-box">{healthResult.error}</div>
          ) : processes ? (
            Object.entries(processes).map(([key, value]) => (
              <Row
                key={key}
                label={key}
                value={String(value)}
                tone={value === "running" ? "good" : undefined}
              />
            ))
          ) : (
            <div className="empty">No process state.</div>
          )}
        </Panel>

        <Panel title="Last Cycles">
          {cycles ? (
            Object.entries(cycles).map(([key, value]) => (
              <Row
                key={key}
                label={key}
                value={String(value ?? "—")}
              />
            ))
          ) : (
            <div className="empty">No cycle state.</div>
          )}
        </Panel>
      </section>

      <section className="grid-2">
        <Panel title="Market Inputs">
          <Row
            label="BTC price"
            value={text(vol, "btc_price")}
          />
          <Row
            label="BTC sigma"
            value={text(vol, "btc_sigma")}
          />
          <Row
            label="ETH price"
            value={text(vol, "eth_price")}
          />
          <Row
            label="ETH sigma"
            value={text(vol, "eth_sigma")}
          />
        </Panel>

        <Panel title="Execution Guardrails">
          <Row
            label="Daily limit"
            value={text(kill, "daily_limit")}
          />
          <Row
            label="Drawdown limit"
            value={text(kill, "drawdown_limit")}
          />
          <Row
            label="Exchange snapshot"
            value="DISABLED"
            tone="warn"
          />
          <Row
            label="Credential state"
            value="ROTATION REQUIRED"
            tone="warn"
          />
          <Row
            label="Velocity API"
            value="127.0.0.1:7777"
            tone="good"
          />
        </Panel>
      </section>

      <section className="panel">
        <div className="panel-title">Dataset Semantics</div>

        <Row
          label="Paper 15m"
          value="Dedicated va_trades ledger"
        />
        <Row
          label="Dry 15m"
          value="Dedicated live_dry ledger"
        />
        <Row
          label="5m"
          value="Single live-mode ledger; legacy /data5m and /dry5m are aliases"
        />
        <Row
          label="Historical live"
          value="Local execution log, not current exchange account truth"
        />
        <Row
          label="Activity reconciliation"
          value="External activity reconstruction; heuristic exit matching"
        />
      </section>
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
      <strong className={tone ? `tone-${tone}` : ""}>
        {value}
      </strong>
    </div>
  );
}
