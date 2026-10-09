import {
  getSignalStatus,
  getVelocityHealth,
  safe,
  type JsonObject,
} from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function OpsPage() {
  const [signalStatus, velocity] = await Promise.all([
    getSignalStatus(),
    safe(getVelocityHealth),
  ]);
  const reliability = signalStatus.reliability;
  const signal = signalStatus.data
    ? { ok: true as const, data: signalStatus.data }
    : { ok: false as const, error: signalStatus.error || "Health unavailable" };

  return (
    <div className="page">
      <header className="page-header">
        <div>
          <div className="eyebrow">OPERATIONS</div>
          <h1>System Health</h1>
          <p>
            Read-only operational state for the SignalAtlas measurement stack
            and VelocityAtlas execution stack.
          </p>
        </div>
      </header>

      <section className="grid-2">
        <HealthPanel
          title="SignalAtlas"
          subtitle="Measurement / outcomes / CLOB"
          reliability={reliability}
          ok={signal.ok}
          data={signal.ok ? signal.data : null}
          error={signal.ok ? null : signal.error}
        />

        <HealthPanel
          title="VelocityAtlas"
          subtitle="Execution / paper / dry-run operations"
          ok={velocity.ok}
          data={velocity.ok ? velocity.data : null}
          error={velocity.ok ? null : velocity.error}
        />
      </section>

      <section className="panel">
        <div className="panel-title">Operational Guardrails</div>

        <div className="metric-row">
          <span>SignalAtlas API</span>
          <strong>127.0.0.1:8011 · READ ONLY</strong>
        </div>

        <div className="metric-row">
          <span>Velocity API</span>
          <strong>127.0.0.1:7777 · LOCAL ONLY</strong>
        </div>

        <div className="metric-row">
          <span>Legacy SignalAtlas dashboard</span>
          <strong className="tone-good">8020 RETIRED</strong>
        </div>

        <div className="metric-row">
          <span>Brain</span>
          <strong className="tone-warn">FAIL-CLOSED</strong>
        </div>

        <div className="metric-row">
          <span>Live Velocity service</span>
          <strong className="tone-warn">DISABLED</strong>
        </div>
      </section>
    </div>
  );
}

function HealthPanel({
  title,
  subtitle,
  ok,
  data,
  error,
  reliability,
}: {
  title: string;
  subtitle: string;
  ok: boolean;
  data: JsonObject | null;
  error: string | null;
  reliability?: "HEALTHY" | "PENDING" | "DEGRADED" | "UNAVAILABLE";
}) {
  const rows = data ? flatten(data).slice(0, 30) : [];

  return (
    <div className="panel">
      <div className="panel-heading">
        <div>
          <div className="panel-title">{title}</div>
          <div className="muted">{subtitle}</div>
        </div>

        <span className={`badge ${reliability === "HEALTHY" ? "badge-good" : reliability === "PENDING" ? "badge-warn" : ok && !reliability ? "badge-good" : "badge-bad"}`}>
          {reliability || (ok ? "ONLINE" : "UNAVAILABLE")}
        </span>
      </div>

      {!ok ? (
        <div className="error-box">{error}</div>
      ) : (
        <div>
          {rows.map(([key, value]) => (
            <div className="metric-row" key={key}>
              <span>{key}</span>
              <strong>{value}</strong>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function flatten(
  obj: JsonObject,
  prefix = "",
  depth = 0
): Array<[string, string]> {
  const out: Array<[string, string]> = [];

  for (const [key, value] of Object.entries(obj)) {
    const name = prefix ? `${prefix}.${key}` : key;

    if (
      value &&
      typeof value === "object" &&
      !Array.isArray(value) &&
      depth < 1
    ) {
      out.push(
        ...flatten(value as JsonObject, name, depth + 1)
      );
      continue;
    }

    if (Array.isArray(value)) {
      out.push([name, `${value.length} items`]);
      continue;
    }

    out.push([name, formatValue(value)]);
  }

  return out;
}

function formatValue(value: unknown): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "boolean") return value ? "true" : "false";
  if (typeof value === "number") return String(value);
  if (typeof value === "string") return value;

  return JSON.stringify(value);
}
