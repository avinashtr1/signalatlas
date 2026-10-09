export type JsonObject = Record<string, unknown>;

const SIGNALATLAS_API =
  process.env.SIGNALATLAS_API_URL || "http://127.0.0.1:8011";

const VELOCITY_API =
  process.env.VELOCITY_API_URL || "http://127.0.0.1:7777";

async function getJson(url: string): Promise<JsonObject> {
  const res = await fetch(url, {
    cache: "no-store",
    signal: AbortSignal.timeout(5000),
  });

  if (!res.ok) {
    throw new Error(`${res.status} ${res.statusText}`);
  }

  const body: unknown = await res.json();

  if (!body || typeof body !== "object" || Array.isArray(body)) {
    throw new Error("Invalid JSON object");
  }

  return body as JsonObject;
}

export async function getSignalHealth() {
  return getJson(`${SIGNALATLAS_API}/api/health`);
}

export type SignalReliability =
  "HEALTHY" | "PENDING" | "DEGRADED" | "UNAVAILABLE";

export async function getSignalStatus(): Promise<{
  reliability: SignalReliability;
  data: JsonObject | null;
  error: string | null;
}> {
  try {
    const response = await fetch(`${SIGNALATLAS_API}/api/health`, {
      cache: "no-store",
      signal: AbortSignal.timeout(5000),
    });

    const body: unknown = await response.json();
    if (!body || typeof body !== "object" || Array.isArray(body)) {
      return { reliability: "UNAVAILABLE", data: null, error: "Invalid health response" };
    }

    const payload = body as JsonObject;
    const measurement = objectValue(payload, "measurement");
    const reliability = objectValue(measurement, "reliability");
    const state = reliability?.state;

    if (response.ok && (state === "HEALTHY" || state === "PENDING")) {
      return { reliability: state, data: payload, error: null };
    }

    const detail = objectValue(payload, "detail");
    if (
      response.status === 503 &&
      detail?.reason === "measurement_reliability_degraded"
    ) {
      return { reliability: "DEGRADED", data: null, error: "Measurement reliability degraded" };
    }

    return { reliability: "UNAVAILABLE", data: null, error: `HTTP ${response.status}` };
  } catch (error) {
    return {
      reliability: "UNAVAILABLE",
      data: null,
      error: error instanceof Error ? error.message : "Health request failed",
    };
  }
}

export async function getMarkets(limit = 100) {
  return getJson(
    `${SIGNALATLAS_API}/api/markets?limit=${Math.max(1, Math.min(limit, 500))}`
  );
}

export async function getVelocityHealth() {
  return getJson(`${VELOCITY_API}/health`);
}

export async function safe<T>(
  fn: () => Promise<T>
): Promise<{ ok: true; data: T } | { ok: false; error: string }> {
  try {
    return { ok: true, data: await fn() };
  } catch (error) {
    return {
      ok: false,
      error: error instanceof Error ? error.message : "unknown error",
    };
  }
}

export function rowsFromResponse(data: JsonObject): JsonObject[] {
  const candidates = [
    data.items,
    data.markets,
    data.rows,
    data.data,
    data.results,
  ];

  for (const candidate of candidates) {
    if (Array.isArray(candidate)) {
      return candidate.filter(
        (x): x is JsonObject =>
          Boolean(x) && typeof x === "object" && !Array.isArray(x)
      );
    }
  }

  return [];
}

export function value(
  row: JsonObject | null | undefined,
  ...keys: string[]
): unknown {
  if (!row) return undefined;

  for (const key of keys) {
    if (key in row) return row[key];
  }

  return undefined;
}

export function text(
  row: JsonObject | null | undefined,
  ...keys: string[]
): string {
  const v = value(row, ...keys);

  if (v === null || v === undefined || v === "") return "—";

  if (typeof v === "string") return v;
  if (typeof v === "number" || typeof v === "boolean") return String(v);

  return "—";
}

export function numberValue(
  row: JsonObject | null | undefined,
  ...keys: string[]
): number | null {
  const v = value(row, ...keys);

  if (typeof v === "number" && Number.isFinite(v)) return v;

  if (typeof v === "string" && v.trim() !== "") {
    const n = Number(v);
    if (Number.isFinite(n)) return n;
  }

  return null;
}

export function formatNumber(
  n: number | null,
  digits = 3
): string {
  return n === null ? "—" : n.toFixed(digits);
}

export async function getMarket(marketId: string) {
  return getJson(
    `${SIGNALATLAS_API}/api/market/${encodeURIComponent(marketId)}`
  );
}

export async function getOrderbook(marketId: string) {
  return getJson(
    `${SIGNALATLAS_API}/api/orderbook/${encodeURIComponent(marketId)}`
  );
}

export async function getMeasurements(marketId: string) {
  return getJson(
    `${SIGNALATLAS_API}/api/measurements/${encodeURIComponent(marketId)}`
  );
}

export async function getForwardOutcomes(marketId: string) {
  return getJson(
    `${SIGNALATLAS_API}/api/forward-outcomes/${encodeURIComponent(marketId)}`
  );
}

export function objectValue(
  row: JsonObject | null | undefined,
  key: string
): JsonObject | null {
  if (!row) return null;

  const v = row[key];

  if (v && typeof v === "object" && !Array.isArray(v)) {
    return v as JsonObject;
  }

  return null;
}

export function arrayValue(
  row: JsonObject | null | undefined,
  key: string
): JsonObject[] {
  if (!row) return [];

  const v = row[key];

  if (!Array.isArray(v)) return [];

  return v.filter(
    (x): x is JsonObject =>
      Boolean(x) && typeof x === "object" && !Array.isArray(x)
  );
}

export async function getVelocityDataset(path: string) {
  if (!path.startsWith("/")) {
    throw new Error("Invalid Velocity API path");
  }

  return getJson(`${VELOCITY_API}${path}`);
}
