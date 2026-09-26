import {
  loadArchitectureDocuments,
  loadRegistrySummaries,
} from "@/lib/architecture";

import {
  getSignalHealth,
  getVelocityHealth,
  safe,
} from "@/lib/api";

export const dynamic = "force-dynamic";

const flow = [
  {
    step: "01",
    title: "Data",
    detail: "Gamma market state + Polymarket CLOB",
  },
  {
    step: "02",
    title: "Measurement",
    detail: "Canonical snapshots + real orderbook metrics",
  },
  {
    step: "03",
    title: "Outcomes",
    detail: "1h / 6h / 24h forward labels as they mature",
  },
  {
    step: "04",
    title: "Health",
    detail: "Collection integrity, freshness and missingness",
  },
  {
    step: "05",
    title: "API",
    detail: "Read-only SignalAtlas interface on localhost",
  },
  {
    step: "06",
    title: "Terminal",
    detail: "EdgeAtlas operator interface",
  },
];

export default async function ArchitecturePage() {
  const [documents, registries, signal, velocity] =
    await Promise.all([
      loadArchitectureDocuments(),
      loadRegistrySummaries(),
      safe(getSignalHealth),
      safe(getVelocityHealth),
    ]);

  const docsAvailable = documents.filter(
    (doc) => doc.available
  ).length;

  const registriesAvailable = registries.filter(
    (registry) => registry.available
  ).length;

  return (
    <div className="page">
      <header className="page-header">
        <div>
          <div className="eyebrow">
            SYSTEM ARCHITECTURE
          </div>

          <h1>SignalAtlas / VelocityAtlas</h1>

          <p>
            Current canonical system map, runtime boundaries,
            registries and roadmap. Architecture metadata is read
            directly from the SignalAtlas registry rather than
            duplicated inside the frontend.
          </p>
        </div>

        <div className="status-line">
          <Status ok={signal.ok}>SignalAtlas</Status>
          <Status ok={velocity.ok}>VelocityAtlas</Status>
        </div>
      </header>

      <section className="kpi-grid">
        <KPI
          label="SignalAtlas API"
          value={signal.ok ? "ONLINE" : "DOWN"}
          sub="127.0.0.1:8011 · read-only"
        />

        <KPI
          label="Velocity API"
          value={velocity.ok ? "ONLINE" : "DOWN"}
          sub="127.0.0.1:7777 · local-only"
        />

        <KPI
          label="Canonical Docs"
          value={`${docsAvailable}/${documents.length}`}
          sub="Loaded from registry"
        />

        <KPI
          label="Registry Files"
          value={`${registriesAvailable}/${registries.length}`}
          sub="Current system metadata"
        />
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <div className="panel-title">
              Canonical Data Path
            </div>

            <div className="muted">
              Business logic remains outside the frontend.
            </div>
          </div>

          <span className="badge badge-good">
            CURRENT
          </span>
        </div>

        <div className="architecture-flow">
          {flow.map((node, index) => (
            <div className="architecture-node" key={node.step}>
              <div className="architecture-step">
                {node.step}
              </div>

              <div className="architecture-node-title">
                {node.title}
              </div>

              <div className="architecture-node-detail">
                {node.detail}
              </div>

              {index < flow.length - 1 && (
                <div className="architecture-arrow">
                  →
                </div>
              )}
            </div>
          ))}
        </div>
      </section>

      <section className="grid-2">
        <Panel title="SignalAtlas">
          <StateRow
            label="Role"
            value="Measurement + Intelligence Infrastructure"
          />

          <StateRow
            label="Measurement API"
            value={
              signal.ok ? "ONLINE" : "UNAVAILABLE"
            }
            tone={signal.ok ? "good" : "bad"}
          />

          <StateRow
            label="Universe coverage"
            value="PARTIAL EVENT SLICE"
          />

          <StateRow
            label="Execution data authority"
            value="CLOB"
          />

          <StateRow
            label="Brain"
            value="FAIL-CLOSED"
            tone="warn"
          />

          <StateRow
            label="Directional alpha"
            value="UNCALIBRATED"
            tone="warn"
          />
        </Panel>

        <Panel title="VelocityAtlas">
          <StateRow
            label="Role"
            value="Permissioned Execution Layer"
          />

          <StateRow
            label="Operational API"
            value={
              velocity.ok ? "ONLINE" : "UNAVAILABLE"
            }
            tone={velocity.ok ? "good" : "bad"}
          />

          <StateRow
            label="Exchange snapshot"
            value="DISABLED"
            tone="warn"
          />

          <StateRow
            label="Credential state"
            value="ROTATION REQUIRED BEFORE LIVE"
            tone="warn"
          />

          <StateRow
            label="Canonical live service"
            value="DISABLED"
          />

          <StateRow
            label="Current role"
            value="PAPER / DRY / HISTORICAL ANALYSIS"
          />
        </Panel>
      </section>

      <section className="panel">
        <div className="panel-title">
          Runtime Boundaries
        </div>

        <div className="runtime-grid">
          <Runtime
            name="EdgeAtlas Web"
            address="127.0.0.1:3030"
            role="Operator terminal"
            status="ACTIVE"
          />

          <Runtime
            name="SignalAtlas API"
            address="127.0.0.1:8011"
            role="Read-only measurements"
            status={signal.ok ? "ACTIVE" : "UNAVAILABLE"}
          />

          <Runtime
            name="Velocity API"
            address="127.0.0.1:7777"
            role="Execution operations"
            status={velocity.ok ? "ACTIVE" : "UNAVAILABLE"}
          />

          <Runtime
            name="Legacy Dashboard"
            address=":8020"
            role="Old static UI"
            status="RETIRED"
          />

          <Runtime
            name="Legacy Web Backend"
            address=":3020"
            role="Old dashboard backend"
            status="RETIRED"
          />

          <Runtime
            name="External Access"
            address="Tailscale HTTPS :8443"
            role="Tailnet-only private EdgeAtlas access"
            status="ACTIVE"
          />
        </div>
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <div className="panel-title">
              Registry Snapshot
            </div>

            <div className="muted">
              Selected operational metadata from the current
              canonical JSON registries.
            </div>
          </div>
        </div>

        <div className="registry-grid">
          {registries.map((registry) => (
            <div
              className="registry-card"
              key={registry.filename}
            >
              <div className="registry-header">
                <span>{registry.filename}</span>

                <span
                  className={`badge ${
                    registry.available
                      ? "badge-good"
                      : "badge-bad"
                  }`}
                >
                  {registry.available
                    ? "LOADED"
                    : "MISSING"}
                </span>
              </div>

              {registry.facts.length === 0 ? (
                <div className="empty">
                  No summarized metadata available.
                </div>
              ) : (
                registry.facts.map(([key, value]) => (
                  <div
                    className="registry-row"
                    key={`${registry.filename}-${key}`}
                  >
                    <span>{key}</span>
                    <strong>{value}</strong>
                  </div>
                ))
              )}
            </div>
          ))}
        </div>
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <div className="panel-title">
              Canonical Documentation
            </div>

            <div className="muted">
              Rendered from the current VPS registry files at
              request time.
            </div>
          </div>
        </div>

        <div className="architecture-docs">
          {documents.map((doc) => (
            <details
              className="architecture-doc"
              key={doc.key}
              open={doc.key === "system_map"}
            >
              <summary>
                <span>{doc.title}</span>

                <span className="doc-file">
                  {doc.filename}
                </span>
              </summary>

              {doc.available ? (
                <pre>{doc.content}</pre>
              ) : (
                <div className="error-box">
                  {doc.filename} unavailable
                </div>
              )}
            </details>
          ))}
        </div>
      </section>

      <section className="panel">
        <div className="panel-title">
          Architecture Discipline
        </div>

        <StateRow
          label="UI"
          value="Presentation only — no trading/business logic"
        />

        <StateRow
          label="Measurement"
          value="Observed truth before modeling"
        />

        <StateRow
          label="Brain"
          value="Remains fail-closed until calibrated evidence exists"
        />

        <StateRow
          label="Execution"
          value="VelocityAtlas remains isolated from SignalAtlas"
        />

        <StateRow
          label="Legacy systems"
          value="Retired paths remain non-canonical"
        />
      </section>
    </div>
  );
}

function Status({
  ok,
  children,
}: {
  ok: boolean;
  children: React.ReactNode;
}) {
  return (
    <>
      <span
        className={`dot ${
          ok ? "dot-good" : "dot-bad"
        }`}
      />
      {children}
    </>
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

function StateRow({
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
      <strong
        className={tone ? `tone-${tone}` : ""}
      >
        {value}
      </strong>
    </div>
  );
}

function Runtime({
  name,
  address,
  role,
  status,
}: {
  name: string;
  address: string;
  role: string;
  status: string;
}) {
  const tone =
    status === "ACTIVE"
      ? "good"
      : status === "RETIRED"
        ? "muted"
        : "warn";

  return (
    <div className="runtime-card">
      <div className="runtime-name">{name}</div>
      <div className="runtime-address">
        {address}
      </div>
      <div className="runtime-role">{role}</div>
      <span className={`badge badge-${tone}`}>
        {status}
      </span>
    </div>
  );
}
